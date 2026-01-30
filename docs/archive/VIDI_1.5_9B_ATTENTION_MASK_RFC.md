# RFC: Vidi 1.5 9B Attention Mask Assertion Failure

## Status: BLOCKED - Cross-Attention Architecture Issue

## Progress Summary

Successfully fixed:
1. ✅ Conv1d and MLP projector dimensions (audio path)
2. ✅ Flash Attention dtype error (vision tower bfloat16)
3. ✅ Image projector shape mismatch (flatten before projection)
4. ✅ Flash cross-attention parameter name (`dropout_p` → `dropout`)

## Current Error

```
AssertionError at xattn.py:86
assert attention_mask_q.shape[1] == query_length
```

**Error Location**: `_unpad_xattn_input()` in `model/lmm/dattn/xattn.py`

**Context**: This occurs during cross-attention between text queries and image features in the first decoder layer.

## Implementation Based on Gemini's Guidance

We implemented the "Extreme Token Compression" strategy as suggested:

```python
# multimodal.py encode_video_images() - CURRENT IMPLEMENTATION

# After pooling: [batch, 2, 2, 1152]
B = image_features.shape[0]
image_features = image_features.reshape(B, -1)  # [batch, 4608]

# Project: [batch, 4608] -> [batch, 3584]
image_features = self.get_model().mm_rand_img_projector(image_features)
image_features = self.get_model().mm_rand_img_norm(image_features)

# Restore to [batch, 1, 3584] for sequence processing
image_features = image_features.unsqueeze(1)  # [batch, 1, 3584]

# Split by video and add temporal positional embeddings
image_features = torch.split(image_features, split_sizes, dim=0)
image_features = [f + rms_norm(self.get_model().mm_rand_pos_t(f, dim=0)) for f in image_features]
image_features = [f.flatten(0, 1) for f in image_features]  # [num_frames, 3584]
image_features = torch.nn.utils.rnn.pad_sequence(image_features, batch_first=True)

# Attention mask computed from actual features
image_attention_mask = (torch.sum(torch.abs(image_features), dim=-1) != 0)
```

**Result**: 1 token per frame (as intended by Gemini's analysis)

## The Assertion Failure

### Code Location (xattn.py lines 29-86)

```python
def _unpad_xattn_input(
    query_layer: torch.Tensor,
    key_layer: torch.Tensor,
    value_layer: torch.Tensor,
    attention_mask_q: torch.Tensor,
    attention_mask_kv: torch.Tensor,
):
    # ... unpacking logic ...

    # Line 86: ASSERTION FAILS HERE
    assert attention_mask_q.shape[1] == query_length
```

### What This Means

The cross-attention mechanism expects:
- `attention_mask_q`: Mask for text queries
- `attention_mask_kv`: Mask for image key/values

The assertion checks that the query attention mask length matches the actual query sequence length.

## Hypothesis: Architecture Mismatch

### Possibility A: Positional Embeddings Still Needed

Gemini suggested removing spatial positional embeddings (`mm_rand_pos_h`, `mm_rand_pos_w`) because they're "degenerate" with 1 token per frame.

**However**: The checkpoint DOES contain these weights (verified earlier).

**Question**: Should we keep the 2x2 spatial grid structure and apply positional embeddings BEFORE flattening?

```python
# Alternative approach:
# After pooling: [batch, 2, 2, 1152]

# Project per-location: [batch, 2, 2, 1152] -> [batch, 2, 2, 3584]
# (This would require changing projector to accept 1152 input)
image_features = self.get_model().mm_rand_img_projector(image_features)

# Apply spatial positional embeddings
image_features = image_features + rms_norm(self.get_model().mm_rand_pos_h(image_features, dim=1))
image_features = image_features + rms_norm(self.get_model().mm_rand_pos_w(image_features, dim=2))

# THEN flatten: [batch, 2, 2, 3584] -> [batch, 4, 3584]
image_features = image_features.reshape(batch, -1, 3584)
```

**Problem**: Checkpoint shows projector is `[3584, 4608]`, not `[3584, 1152]`.

### Possibility B: Cross-Attention Expects Different Input Format

The assertion failure suggests the cross-attention mechanism might expect:
- Multiple tokens per frame (not 1)
- Specific attention mask format
- Different sequence packing

**Question**: Does Vidi 1.5 9B actually use 1 token per frame, or does it use 4 tokens (2x2 grid)?

## Evidence to Examine

### 1. Checkpoint Weights

```
model.mm_rand_img_projector.model.0.weight: torch.Size([3584, 4608])
model.mm_rand_pos_h.mlp.0.weight: EXISTS
model.mm_rand_pos_w.mlp.0.weight: EXISTS
model.mm_rand_pos_t.mlp.0.weight: EXISTS
```

**Interpretation**:
- Projector expects 4608 input → suggests flattening IS correct
- Spatial positional embeddings exist → suggests 2x2 grid IS preserved

**Contradiction**: How can we both flatten (4608 input) AND preserve spatial structure (for pos embeddings)?

### 2. Original Vidi 7B Code

If we had access to working Vidi 7B code, we could compare:
- Does it flatten before or after positional embeddings?
- How many tokens per frame does it output?
- What's the projector input dimension?

## Questions for Deep Research

1. **Token Compression Strategy**:
   - Does Vidi 1.5 9B really use 1 token per frame?
   - Or does it use 4 tokens (2x2 grid) per frame?
   - When does flattening happen in the pipeline?

2. **Positional Embedding Application**:
   - Are spatial positional embeddings applied before or after flattening?
   - If applied after flattening, how do they work with 1D sequence?
   - Should we reshape back to 2x2 grid for positional embeddings?

3. **Projector Architecture**:
   - Why is projector input 4608 if we need spatial structure?
   - Is there a reshape operation after projection?
   - Does the projector output get reshaped to [batch, 2, 2, 3584]?

4. **Cross-Attention Compatibility**:
   - What sequence format does cross-attention expect?
   - Should image features be [batch, num_frames, 3584] or [batch, num_frames*4, 3584]?
   - How should attention masks be structured?

## Proposed Investigation

### Option 1: Keep Spatial Structure Throughout

```python
# After pooling: [batch, 2, 2, 1152]

# Reshape for projection: [batch*2*2, 1152]
B, H, W, C = image_features.shape
image_features = image_features.reshape(B*H*W, C)

# Project: [batch*4, 1152] -> [batch*4, 3584]
# But wait, projector expects 4608 input...
```

**Problem**: Projector dimension mismatch.

### Option 2: Flatten, Project, Reshape

```python
# After pooling: [batch, 2, 2, 1152]

# Flatten: [batch, 4608]
image_features = image_features.reshape(B, -1)

# Project: [batch, 4608] -> [batch, 3584]
image_features = self.get_model().mm_rand_img_projector(image_features)

# Reshape back to spatial: [batch, 2, 2, 896]?
# (3584 / 4 = 896 features per location)
image_features = image_features.reshape(B, 2, 2, -1)

# Apply positional embeddings
image_features = image_features + rms_norm(self.get_model().mm_rand_pos_h(image_features, dim=1))
image_features = image_features + rms_norm(self.get_model().mm_rand_pos_w(image_features, dim=2))

# Flatten again: [batch, 4, 896]
image_features = image_features.reshape(B, 4, -1)
```

**Question**: Is this the correct interpretation?

## Request

Please analyze:
1. The correct sequence of operations for image feature processing
2. When and how flattening should occur
3. How positional embeddings fit into the pipeline
4. What the final image feature shape should be before cross-attention
5. Whether we should output 1 token or 4 tokens per frame

The checkpoint evidence (projector=4608, pos_h/w exist) seems contradictory with the "1 token per frame" interpretation. Please clarify the architecture.

Thank you!
