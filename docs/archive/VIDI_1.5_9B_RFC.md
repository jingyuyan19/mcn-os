# RFC: Vidi 1.5 9B Integration Issue - Request for Comments

## Executive Summary

We are attempting to upgrade from Vidi 7B (Mistral-based) to Vidi 1.5 9B (Gemma 2-based) for video understanding tasks. The model weights have been successfully downloaded (20GB), but we're encountering architecture mismatch errors during model loading. We need guidance on the correct model architecture implementation for Vidi 1.5 9B.

## Background

**Project**: MCN OS - Cognitive Operating System for AI-generated video content
**Component**: Vidi Client - Video understanding and temporal retrieval
**Hardware**: NVIDIA RTX 4090 24GB
**Environment**: Python 3.12, PyTorch 2.9.1+cu128, transformers 4.57.6

## Current State

### Successfully Completed
1. ✅ Downloaded Vidi 1.5 9B model weights (20GB) from HuggingFace `bytedance-research/Vidi1.5-9B`
2. ✅ Stored weights on SSD at `/mnt/data_ssd/models/Vidi/Vidi-1.5-9B`
3. ✅ Installed dependencies: liger-kernel 0.6.4, transformers 4.57.6, flash-attn 2.6.3
4. ✅ Downloaded official Gemma 2 implementation files from GitHub:
   - `model/lmm/dattn/gemma.py` (DattnGemma2ForCausalLM)
   - `model/lmm/dattn/utils.py`
   - `model/lmm/dattn/ctx_fn.py`
   - `model/lmm/dattn/sequence_parallel/` (full directory)
   - `model/lmm/dattn/split.py`
5. ✅ Updated `model/__init__.py` to use `DattnGemma2ForCausalLM` instead of `DattnMistralForCausalLM`
6. ✅ Fixed import paths (changed `from vidi.constants` to `from model.constants`)

### Current Blocker

**Shape Mismatch Error** during model loading:

```
RuntimeError: Error(s) in loading state_dict for Conv1d:
	size mismatch for weight: copying a param with shape torch.Size([3584, 1280, 5])
	from checkpoint, the shape in current model is torch.Size([1280, 1280, 5]).
```

**Layer**: `model.mm_rand_aud_pool` (audio pooling Conv1d layer)

## Technical Analysis

### Model Architecture Specifications

**Vidi 1.5 9B Configuration** (from `config.json`):
```json
{
  "hidden_size": 3584,              // Gemma 2 9B hidden size
  "num_hidden_layers": 42,          // Gemma 2 9B layers
  "mm_audio_tower": "openai/whisper-large-v3",  // Audio encoder (hidden_size=1280)
  "mm_vision_tower": "google/siglip2-so400m-patch14-384",  // Vision encoder
  "mm_audio_pool_size": 5,          // Audio pooling kernel size
  "mm_image_pool_size": 2,          // Image pooling size
  "mm_projector_type": null
}
```

### Checkpoint Analysis

Inspected `model-00005-of-00005.safetensors` and found:

**Audio-related layers**:
- `model.mm_aud.encoder.*` - Whisper Large v3 encoder (32 layers, hidden_size=1280)
- `model.mm_rand_aud_pool.weight` - **Shape: [3584, 1280, 5]**
- `model.mm_rand_aud_projector.model.0.weight` - MLP projector
- `model.mm_rand_aud_norm.weight` - RMSNorm

**Key Finding**: The checkpoint's `mm_rand_aud_pool` has:
- `out_channels=3584` (Gemma 2's hidden_size)
- `in_channels=1280` (Whisper's hidden_size)
- `kernel_size=5`

### Current Code Implementation

**File**: `model/lmm/dattn/multimodal.py` (lines 82-90)

```python
assert config.mm_audio_pool_size is not None
self.mm_rand_aud_pool = nn.Conv1d(
    self.mm_aud.hidden_size,      # in_channels=1280 (Whisper)
    self.mm_aud.hidden_size,      # out_channels=1280 (WRONG!)
    bias=False,
    kernel_size=config.mm_audio_pool_size,  # 5
    stride=config.mm_audio_pool_size        # 5
)
self.mm_rand_aud_projector = MLP(
    config.mm_projector_type,     # None in config
    self.mm_aud.hidden_size,      # 1280
    config.hidden_size            # 3584
)
self.mm_rand_aud_norm = RMSNorm(config.hidden_size)  # 3584
```

**Problem**: The code creates Conv1d with `[1280, 1280, 5]` but checkpoint has `[3584, 1280, 5]`.

## Architecture Questions

### Question 1: Audio Processing Pipeline Order

**Current code suggests**:
```
Whisper (1280) → Conv1d Pool [1280→1280] → MLP Project [1280→3584] → RMSNorm (3584)
```

**Checkpoint suggests**:
```
Whisper (1280) → Conv1d Pool [1280→3584] → ??? → RMSNorm (3584)
```

**Question**: Should the Conv1d pooling layer:
- A) Pool within the same dimension (1280→1280) then project to 3584?
- B) Pool AND project simultaneously (1280→3584)?

### Question 2: MLP Projector Role

The config has `mm_projector_type: null`, but the code creates an MLP projector. The checkpoint contains:
- `model.mm_rand_aud_projector.model.0.weight`
- `model.mm_rand_aud_projector.model.0.bias`
- `model.mm_rand_aud_projector.model.2.weight`
- `model.mm_rand_aud_projector.model.2.bias`

**Question**: If Conv1d already projects to 3584, what does the MLP projector do?

### Question 3: Vidi 7B vs 1.5 9B Differences

**Vidi 7B** (Mistral-based, hidden_size=1280):
- Conv1d: [1280, 1280, 5] - no dimension change
- MLP: [1280, 1280] - no dimension change

**Vidi 1.5 9B** (Gemma 2-based, hidden_size=3584):
- Conv1d: [3584, 1280, 5] - projects UP during pooling
- MLP: [?, ?] - unclear role

**Question**: Did the architecture fundamentally change between versions?

## What We Need

### Primary Request

**Correct implementation of `multimodal.py` for Vidi 1.5 9B**, specifically:

1. Correct Conv1d configuration for `mm_rand_aud_pool`
2. Correct MLP configuration for `mm_rand_aud_projector` (if needed)
3. Correct processing order for audio features

### Secondary Requests

1. **Official Vidi 1.5 9B code**: Is there an official `multimodal.py` for Vidi 1.5 9B?
   - GitHub repo only shows Vidi 7B implementation
   - HuggingFace model repo doesn't include Python files

2. **Architecture documentation**: Any papers, docs, or READMEs explaining the Vidi 1.5 9B architecture changes?

3. **Similar implementations**: Are there other Gemma 2-based multimodal models we can reference?

## Attempted Solutions

### Attempt 1: Use Vidi 7B code directly
- **Result**: Shape mismatch (expected, different architectures)

### Attempt 2: Download official Gemma 2 files
- **Result**: Fixed some imports, but multimodal.py still from Vidi 7B

### Attempt 3: Analyze checkpoint structure
- **Result**: Identified the shape mismatch, but unclear on correct fix

## Proposed Fix (Needs Validation)

**Option A**: Change Conv1d to project during pooling
```python
self.mm_rand_aud_pool = nn.Conv1d(
    self.mm_aud.hidden_size,      # in_channels=1280
    config.hidden_size,            # out_channels=3584 (CHANGED)
    bias=False,
    kernel_size=config.mm_audio_pool_size,
    stride=config.mm_audio_pool_size
)
# Remove or modify MLP projector?
```

**Option B**: Add pre-projection before Conv1d
```python
self.mm_rand_aud_pre_proj = nn.Linear(
    self.mm_aud.hidden_size,      # 1280
    config.hidden_size             # 3584
)
self.mm_rand_aud_pool = nn.Conv1d(
    config.hidden_size,            # in_channels=3584
    config.hidden_size,            # out_channels=3584
    bias=False,
    kernel_size=config.mm_audio_pool_size,
    stride=config.mm_audio_pool_size
)
```

**Question**: Which approach is correct for Vidi 1.5 9B?

## Resources

### GitHub Repositories
- Main repo: https://github.com/bytedance/vidi
- Vidi 1.5 9B directory: https://github.com/bytedance/vidi/tree/main/Vidi1.5_9B
- Note: Public repo doesn't contain full model implementation

### HuggingFace
- Model: https://huggingface.co/bytedance-research/Vidi1.5-9B
- Contains: Weights, config.json, tokenizer files
- Missing: Python implementation files

### Local Files
- Model weights: `/mnt/data_ssd/models/Vidi/Vidi-1.5-9B/`
- Code: `/home/jimmy/Documents/mcn/external/Vidi/Vidi_1.5_9B/`
- Current multimodal.py: Adapted from Vidi 7B (likely incorrect)

## Request to Research Agent

Please investigate:

1. **Find official Vidi 1.5 9B implementation** of `multimodal.py` or equivalent
2. **Explain the architecture change** from Vidi 7B to 1.5 9B for audio processing
3. **Provide correct Conv1d configuration** for `mm_rand_aud_pool` layer
4. **Clarify MLP projector role** when `mm_projector_type` is null
5. **Suggest working implementation** that matches the checkpoint structure

## Success Criteria

A working implementation that:
1. Loads the Vidi 1.5 9B checkpoint without shape mismatch errors
2. Successfully runs inference on a 10-second test video
3. Returns temporal retrieval results (timestamps) for a query like "phone"

## Contact & Follow-up

This RFC will be sent to Gemini Deep Research agent for analysis. Any findings, code samples, or architectural insights would be greatly appreciated.

---

**Generated**: 2026-01-30
**Status**: Awaiting research agent response
**Priority**: High - Blocking Vidi 1.5 9B integration
