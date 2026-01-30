# RFC: Vidi 1.5 9B Device Placement Issue - Request for Comments

## Executive Summary

We successfully resolved the shape mismatch errors in Vidi 1.5 9B integration (thanks to previous RFC guidance). The model now loads, but we're encountering a device placement error where some parameters remain on the "meta" device instead of being moved to CUDA. We need guidance on proper device management for large multimodal models.

## Background

**Project**: MCN OS - Cognitive Operating System for AI-generated video content
**Component**: Vidi Client - Video understanding and temporal retrieval
**Hardware**: NVIDIA RTX 4090 24GB
**Environment**: Python 3.12, PyTorch 2.9.1+cu128, transformers 4.57.6

## Current State

### ✅ Successfully Completed (Previous RFC)
1. Fixed audio Conv1d layer: `[1280, 1280, 5]` → `[3584, 1280, 5]`
2. Fixed audio MLP projector: input `1280` → `3584`
3. Fixed image MLP projector: input `1152` → `4608`
4. **Model loads without shape mismatch errors!**

### 🔴 Current Blocker: Device Placement Error

**Error Message**:
```
Some parameters are on the meta device device because they were offloaded to the cpu.
RuntimeError: Tensor on device meta is not on the expected device cuda:0!
```

**Full Stack Trace**:
```python
File "/mnt/data_ssd/mcn/external/Vidi/Vidi_1.5_9B/inference.py", line 107, in <module>
    print(ask(args.query, args.video_path, model, tokenizer, image_processor, audio_processor, task=args.task))
File "/mnt/data_ssd/mcn/external/Vidi/Vidi_1.5_9B/inference.py", line 49, in ask
    output_ids = model.generate(...)
File "/mnt/data_ssd/mcn/external/Vidi/Vidi_1.5_9B/model/lmm/dattn/gemma.py", line 630, in generate
    ) = self.prepare_inputs_labels_for_multimodal(...)
File "/mnt/data_ssd/mcn/external/Vidi/Vidi_1.5_9B/model/lmm/dattn/multimodal.py", line 425, in prepare_inputs_labels_for_multimodal
    self.encode_multimodal_inputs(images, image_sizes, audios, audio_sizes)
File "/mnt/data_ssd/mcn/external/Vidi/Vidi_1.5_9B/model/lmm/dattn/multimodal.py", line 138, in encode_multimodal_inputs
    return self.encode_videos(images, audios, audio_sizes)
File "/mnt/data_ssd/mcn/external/Vidi/Vidi_1.5_9B/model/lmm/dattn/multimodal.py", line 241, in encode_videos
    image_features, image_attention_mask = self.encode_video_images(images)
File "/mnt/data_ssd/mcn/external/Vidi/Vidi_1.5_9B/model/lmm/dattn/multimodal.py", line 170, in encode_video_images
    _, image_features = splitted_call(...)
File "/mnt/data_ssd/mcn/external/Vidi/Vidi_1.5_9B/model/lmm/dattn/split.py", line 49, in splitted_call
    o = func(x)
File ".../transformers/models/siglip/modeling_siglip.py", line 708, in forward
    pooler_output = self.head(last_hidden_state) if self.use_head else None
File ".../transformers/models/siglip/modeling_siglip.py", line 731, in forward
    hidden_state = self.attention(probe, hidden_state, hidden_state)[0]
...
RuntimeError: Tensor on device meta is not on the expected device cuda:0!
```

**Error Location**: Inside SigLIP vision tower's attention mechanism during forward pass.

## Technical Analysis

### Model Loading Process

**Current Code** (`model/builder.py`):
```python
def load_pretrained_model(model_path, model_base=None, model_name=None, load_8bit=False, load_4bit=False, device_map="auto", device="cuda", **kwargs):
    # ... tokenizer loading ...

    LMM_CLS = get_dattn_cls(model_path)

    # Load model with device_map="auto"
    model = LMM_CLS.from_pretrained(
        model_path,
        low_cpu_mem_usage=True,
        device_map=device_map,  # "auto" by default
        torch_dtype=torch.bfloat16,
        attn_implementation="flash_attention_2",
        **kwargs
    )

    # ... processor loading ...

    return model, tokenizer, image_processor, audio_processor
```

**Inference Code** (`inference.py`):
```python
# Load model
model, tokenizer, image_processor, audio_processor = load_pretrained_model(
    args.model_path,
    device_map="auto",
    device="cuda"
)

# Prepare inputs
input_ids = tokenizer_image_audio_token(...)
images = process_images(...)
audios = process_audios(...)

# Generate (ERROR OCCURS HERE)
output_ids = model.generate(
    input_ids,
    images=images,
    audios=audios,
    image_sizes=image_sizes,
    audio_sizes=audio_sizes,
    ...
)
```

### Device Placement Analysis

**Warning Message**: "Some parameters are on the meta device device because they were offloaded to the cpu."

This suggests:
1. Model is too large for single GPU (but 20GB model on 24GB GPU should fit)
2. `device_map="auto"` is offloading some layers to CPU
3. During forward pass, tensors on different devices are being mixed

**Hypothesis**: The vision tower (SigLIP) or audio tower (Whisper) may have parameters on CPU/meta device, while the main model is on CUDA.

### Model Size Breakdown

**Total Model Size**: ~20GB
- Gemma 2 9B base: ~18GB (bfloat16)
- SigLIP 2 SO400M: ~800MB
- Whisper Large v3: ~1.5GB
- Multimodal adapters: ~200MB

**Available VRAM**: 24GB on RTX 4090

**Expected**: Should fit entirely on GPU with ~4GB headroom.

## Questions for Research Agent

### Question 1: Device Map Strategy

**Current**: Using `device_map="auto"` which may be offloading unnecessarily.

**Options**:
- A) Force all to CUDA: `device_map={"": "cuda:0"}` or `device_map="cuda:0"`
- B) Explicit device map: Specify which modules go where
- C) Sequential loading: Load base model first, then move towers to CUDA
- D) Disable offloading: Use `low_cpu_mem_usage=False`

**Question**: Which strategy is correct for Vidi 1.5 9B on a 24GB GPU?

### Question 2: Meta Device Issue

The error mentions "meta device" specifically. In PyTorch/Transformers:
- Meta device is used for lazy initialization (weights not allocated)
- Should be materialized to actual device before use

**Question**: Why are some parameters still on meta device after `from_pretrained()`? Is this a:
- A) Bug in our model loading code?
- B) Issue with how multimodal towers are initialized?
- C) Problem with `device_map="auto"` logic?
- D) Missing explicit `.to(device)` call somewhere?

### Question 3: Multimodal Tower Device Placement

The error occurs in SigLIP's attention layer. This suggests the vision tower may not be properly moved to CUDA.

**Code Context** (`multimodal.py`):
```python
def __init__(self, config):
    # Vision tower
    self.mm_vis = vision_tower.from_pretrained(
        config.mm_vision_tower,
        select_layer=config.mm_vision_select_layer,
        attn_implementation="sdpa"
    )

    # Audio tower
    self.mm_aud = audio_tower.from_pretrained(
        config.mm_audio_tower,
        attn_implementation="sdpa"
    )
```

**Question**: Do we need to explicitly move towers to CUDA after initialization? Should we add:
```python
self.mm_vis = self.mm_vis.to(device)
self.mm_aud = self.mm_aud.to(device)
```

### Question 4: Input Tensor Device Placement

**Current Code** (`inference.py`):
```python
images = process_images([video_frames], image_processor, model.config)
audios = process_audios([audio_data], audio_processor)
```

**Question**: Do input tensors (images, audios) need explicit `.to("cuda")` calls? Or does `model.generate()` handle this automatically?

### Question 5: Accelerate Integration

The stack trace shows `accelerate/hooks.py` is involved. Accelerate is used for device management in Transformers.

**Question**: Is there a conflict between:
- Manual device placement (`device="cuda"`)
- Accelerate's automatic device management (`device_map="auto"`)
- Flash Attention 2 requirements

Should we disable Accelerate or configure it differently?

## Attempted Solutions (Hypothetical)

### Attempt 1: Force Single Device
```python
model = LMM_CLS.from_pretrained(
    model_path,
    device_map={"": "cuda:0"},  # Force all to CUDA
    torch_dtype=torch.bfloat16,
    attn_implementation="flash_attention_2"
)
```

**Expected**: All parameters on CUDA, no offloading.
**Risk**: May fail if model doesn't fit (but should fit on 24GB).

### Attempt 2: Explicit Device Movement
```python
model = LMM_CLS.from_pretrained(...)
model = model.to("cuda")  # Explicit move
```

**Expected**: Override any device_map decisions.
**Risk**: May conflict with Accelerate hooks.

### Attempt 3: Disable Low CPU Memory Mode
```python
model = LMM_CLS.from_pretrained(
    model_path,
    low_cpu_mem_usage=False,  # Disable lazy loading
    device_map="cuda:0",
    torch_dtype=torch.bfloat16
)
```

**Expected**: No meta device, direct CUDA allocation.
**Risk**: Higher memory usage during loading.

### Attempt 4: Move Input Tensors Explicitly
```python
images = images.to("cuda")
audios = audios.to("cuda")
input_ids = input_ids.to("cuda")

output_ids = model.generate(
    input_ids,
    images=images,
    audios=audios,
    ...
)
```

**Expected**: Ensure all inputs on same device as model.
**Risk**: May not solve the issue if model parameters are on wrong device.

## Related Issues & References

### Similar Issues in Transformers
- Large models with `device_map="auto"` sometimes offload unnecessarily
- Meta device issues often related to lazy initialization
- Flash Attention 2 requires all tensors on CUDA

### Vidi-Specific Considerations
- Multimodal models have multiple towers (vision, audio, text)
- Each tower may be loaded separately and need device coordination
- Video processing involves large tensor batches

### PyTorch Device Management
- `device_map="auto"`: Accelerate decides placement
- `device_map={"": "cuda:0"}`: Force all to single device
- `device_map=None`: No automatic placement (manual `.to()` needed)

## What We Need

### Primary Request

**Working device placement strategy** for Vidi 1.5 9B that:
1. Loads all model parameters to CUDA (no CPU/meta offloading)
2. Handles multimodal towers (SigLIP, Whisper) correctly
3. Works with Flash Attention 2
4. Fits in 24GB VRAM

### Secondary Requests

1. **Explanation of meta device issue**: Why are parameters on meta device after loading?
2. **Best practices for multimodal models**: How to ensure all towers are on same device?
3. **Input tensor handling**: Should inputs be explicitly moved to CUDA?
4. **Accelerate configuration**: Any special settings needed for Vidi?

## Success Criteria

A working implementation that:
1. Loads Vidi 1.5 9B completely on CUDA (no meta/CPU tensors)
2. Successfully runs inference on a 10-second test video
3. Returns temporal retrieval results (timestamps) for query "phone"
4. Uses available 24GB VRAM efficiently

## Environment Details

### Hardware
- GPU: NVIDIA RTX 4090 (24GB VRAM)
- RAM: Sufficient for model loading
- Storage: SSD with model weights

### Software
- PyTorch: 2.9.1+cu128
- Transformers: 4.57.6
- Accelerate: (version from transformers dependencies)
- Flash Attention: 2.6.3
- CUDA: 12.8

### Model Files
- Location: `/mnt/data_ssd/models/Vidi/Vidi-1.5-9B/`
- Size: 20GB (5 safetensors shards)
- Format: bfloat16

## Code Files

### Main Files
- **Model loading**: `/home/jimmy/Documents/mcn/external/Vidi/Vidi_1.5_9B/model/builder.py`
- **Inference**: `/home/jimmy/Documents/mcn/external/Vidi/Vidi_1.5_9B/inference.py`
- **Multimodal**: `/home/jimmy/Documents/mcn/external/Vidi/Vidi_1.5_9B/model/lmm/dattn/multimodal.py`
- **Gemma model**: `/home/jimmy/Documents/mcn/external/Vidi/Vidi_1.5_9B/model/lmm/dattn/gemma.py`

### Test Command
```bash
cd /home/jimmy/Documents/mcn/external/Vidi/Vidi_1.5_9B
HF_ENDPOINT=https://hf-mirror.com \
/home/jimmy/Documents/mcn/middleware/.venv/bin/python3 -u inference.py \
  --video-path /home/jimmy/Documents/mcn/test_output/phone_review_10s.mp4 \
  --query "phone" \
  --model-path /home/jimmy/Documents/mcn/external/Vidi/Vidi_1.5_9B/weights \
  --task retrieval
```

## Request to Research Agent

Please investigate:

1. **Root cause of meta device issue** in Vidi 1.5 9B loading
2. **Correct device_map configuration** for 24GB single GPU
3. **Multimodal tower device placement** best practices
4. **Input tensor device handling** requirements
5. **Working code example** that resolves the device placement error

Focus on practical, implementable solutions that work with the existing Vidi 1.5 9B architecture.

## Additional Context

### Previous Success
- Vidi 7B worked fine with similar loading code
- Shape mismatch issues were successfully resolved
- Model architecture is now correct (verified against checkpoint)

### Current Hypothesis
The issue is likely one of:
1. `device_map="auto"` being too conservative and offloading unnecessarily
2. Multimodal towers not being moved to CUDA during initialization
3. Input tensors not being on the same device as model
4. Conflict between Accelerate and manual device placement

---

**Generated**: 2026-01-30
**Status**: Awaiting research agent response
**Priority**: High - Final blocker for Vidi 1.5 9B integration
**Previous RFC**: Successfully resolved shape mismatch issues
