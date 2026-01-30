# RFC: Vidi 1.5 9B Image Projector Shape Mismatch

## Status: BLOCKED - Need Architectural Guidance

## Context

After successfully fixing:
1. ✅ Conv1d and MLP projector dimension mismatches (audio path)
2. ✅ Flash Attention dtype error (vision tower loading)

We now encounter a **shape mismatch in the image projector** during inference.

## Current Error

```
RuntimeError: mat1 and mat2 shapes cannot be multiplied (20x1152 and 4608x3584)
```

**Error Location**: `multimodal.py:182` in `encode_video_images()`

```python
image_features = self.get_model().mm_rand_img_projector(image_features)
```

**Actual Input Shape**: `[20, 1152]` (20 patches, 1152 features each)
**Expected Input Shape**: `[20, 4608]` (20 patches, 4608 features = 1152 * 4)

## Architecture Analysis

### Image Processing Pipeline (multimodal.py lines 164-197)

```python
def encode_video_images(self, images):
    # 1. Vision tower forward pass
    _, image_features = splitted_call(
        self.get_model().mm_vis, concat_images, self.config.mm_splits
    )
    # Output: [batch, num_patches, 1152] where num_patches = 27*27 = 729

    # 2. Reshape to spatial grid
    height = width = self.mm_vis.num_patches_per_side  # 27
    image_features = image_features.reshape(len(image_features), height, width, -1)
    # Shape: [batch, 27, 27, 1152]

    # 3. Permute for Conv2D
    image_features = image_features.permute(0, 3, 1, 2)
    # Shape: [batch, 1152, 27, 27]

    # 4. Spatial pooling
    image_features = splitted_call(
        self.get_model().mm_rand_img_pool, image_features, self.config.mm_splits
    )
    # Shape: [batch, 1152, pool_size, pool_size] where pool_size = 2
    # Output: [batch, 1152, 2, 2]

    # 5. Permute back
    image_features = image_features.permute(0, 2, 3, 1)
    # Shape: [batch, 2, 2, 1152]

    # 6. ❌ ERROR HERE: Projector expects [batch, 2, 2, 4608]
    image_features = self.get_model().mm_rand_img_projector(image_features)
```

### Conv2DPool Implementation (pool.py)

```python
class Conv2DPool(nn.Module):
    def __init__(self, d_in, d_out, s_in, s_out):
        super().__init__()
        self.d_in = d_in      # 1152
        self.d_out = d_out    # 1152 (same as d_in)
        self.s_in = s_in      # 27
        self.s_out = s_out    # 2
        self.conv = nn.Conv2d(
            d_in, d_out, bias=False, kernel_size=math.ceil(s_in / s_out)
        )

    def forward(self, x):
        x = self.conv(x)  # Spatial reduction via Conv2D
        x = F.interpolate(x, size=self.s_out, mode='bilinear', align_corners=True)
        return x
```

**Key Observation**: Conv2DPool keeps channels constant (d_in=d_out=1152), only reduces spatial dimensions.

### Projector Initialization (multimodal.py lines 67-77)

```python
self.mm_rand_img_pool = Conv2DPool(
    d_in=self.mm_vis.hidden_size,      # 1152
    d_out=self.mm_vis.hidden_size,     # 1152
    s_in=self.mm_vis.num_patches_per_side,  # 27
    s_out=config.mm_image_pool_size    # 2
)

# Projector expects flattened pooled patches
img_projector_input_dim = self.mm_vis.hidden_size * (config.mm_image_pool_size ** 2)
# img_projector_input_dim = 1152 * (2 ** 2) = 1152 * 4 = 4608

self.mm_rand_img_projector = MLP(
    projector_type,
    img_projector_input_dim,  # 4608
    config.hidden_size         # 3584
)
```

## The Discrepancy

**Projector Initialization Logic**:
- Assumes input will be **flattened pooled patches**: `1152 * (pool_size^2) = 1152 * 4 = 4608`
- This suggests: `[batch, pool_size, pool_size, 1152]` → flatten last 3 dims → `[batch, 4608]`

**Actual Pipeline**:
- After pooling: `[batch, pool_size, pool_size, 1152]`
- Directly passed to projector without flattening
- Projector receives: `[batch*pool_size*pool_size, 1152]` = `[20, 1152]` (for batch=5, pool_size=2)

## Hypothesis

There are two possible interpretations:

### Hypothesis A: Missing Flatten Operation
The pipeline should flatten the spatial dimensions before projection:

```python
# After pooling and permute: [batch, 2, 2, 1152]
image_features = image_features.reshape(batch, 2, 2, 1152)

# Flatten spatial + channel dims: [batch, 2*2*1152] = [batch, 4608]
image_features = image_features.reshape(batch, -1)

# Now projector can accept: [batch, 4608] → [batch, 3584]
image_features = self.get_model().mm_rand_img_projector(image_features)

# Reshape back to spatial: [batch, 3584] → [batch, 1, 1, 3584]?
```

**Problem**: This would lose spatial structure, but later code expects spatial dimensions (lines 184-185 apply positional embeddings per height/width).

### Hypothesis B: Wrong Projector Input Dimension
The projector should accept `1152` per spatial location, not `4608` total:

```python
# Projector should be: [1152 → 3584] per spatial location
self.mm_rand_img_projector = MLP(
    projector_type,
    self.mm_vis.hidden_size,  # 1152 (not 4608)
    config.hidden_size         # 3584
)
```

**Problem**: This contradicts the checkpoint weights which show projector first layer is `[3584, 4608]`.

## Checkpoint Evidence

From previous analysis (VIDI_1.5_9B_SUCCESS_SUMMARY.md):

```
model.mm_rand_img_projector.model.0.weight: torch.Size([3584, 4608])
model.mm_rand_img_projector.model.2.weight: torch.Size([3584, 3584])
```

**Confirmed**: Projector first layer expects **4608 input features**, not 1152.

## Questions for Deep Research

1. **Spatial Flattening Strategy**:
   - Should the pooled features be flattened before projection?
   - If yes, how are spatial positional embeddings applied afterward?
   - Does the model use a "flatten → project → reshape" pattern?

2. **Vidi 7B vs 1.5 9B Comparison**:
   - How does Vidi 7B handle this? (It worked in previous version)
   - Did the architecture change between versions?
   - Is there a reshape operation we're missing?

3. **"Project while Pooling" for Images**:
   - Audio uses "project while pooling" (Conv1d projects 1280→3584)
   - Should images also project during pooling (Conv2D projects 1152→4608)?
   - Or is the projection separate (pool first, then project)?

4. **Positional Embedding Compatibility**:
   - Lines 184-185 apply positional embeddings per spatial dimension:
     ```python
     image_features = image_features + rms_norm(self.get_model().mm_rand_pos_h(image_features, dim=1))
     image_features = image_features + rms_norm(self.get_model().mm_rand_pos_w(image_features, dim=2))
     ```
   - This requires spatial structure: `[batch, height, width, features]`
   - How can we flatten to `[batch, 4608]` and still have spatial dims?

5. **Correct Pipeline Flow**:
   - What is the intended shape at each step?
   - Is there a missing reshape/view operation?
   - Should the projector operate per-patch or on flattened features?

## Relevant Code Files

1. **multimodal.py** (lines 64-77): Projector initialization
2. **multimodal.py** (lines 164-197): encode_video_images pipeline
3. **pool.py**: Conv2DPool implementation
4. **mlp.py**: MLP projector implementation

## Test Case

**Video**: `/home/jimmy/Documents/mcn/assets/videos/avatar_default.mp4`
**Query**: "What is in this video?"
**Task**: VQA (Video Question Answering)

## Success Criteria

- Image features successfully pass through projector
- Spatial positional embeddings apply correctly
- Model generates coherent response to video query
- No shape mismatch errors

## Request

Please analyze the Vidi 1.5 9B architecture and provide guidance on:
1. The correct shape transformation pipeline for image features
2. Whether flattening is needed before projection
3. How to maintain spatial structure for positional embeddings
4. Any missing reshape operations in the current implementation

Thank you!
