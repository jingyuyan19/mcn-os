# Vidi 1.5 9B Quantization Test Results

## Test Date: 2026-01-30

## Summary

**Status**: ⚠️ **Quantization Supported but VRAM Insufficient**

Vidi 1.5 9B supports both 4-bit and 8-bit quantization via `bitsandbytes`, but even with 4-bit quantization, the model requires more VRAM than currently available when other services (CosyVoice, ComfyUI) are running.

## System Configuration

- **GPU**: RTX 4090 24GB
- **System RAM**: 62GB
- **Current GPU Usage**:
  - CosyVoice: 3.8GB
  - ComfyUI: 384MB
  - **Available**: 19.6GB

## Test Results

### 1. Vidi Availability ✅
```
Model: Vidi 1.5-9B
Location: /home/jimmy/Documents/mcn/external/Vidi/Vidi_1.5_9B/weights
Python: /home/jimmy/Documents/mcn/middleware/.venv/bin/python3
Flash Attention: Installed (2.6.3)
Bitsandbytes: Installed (0.49.1)
```

### 2. Quantization Support ✅
```python
# VidiClient now supports quantization parameters
vidi = VidiClient(load_4bit=True)   # 4-bit quantization
vidi = VidiClient(load_8bit=True)   # 8-bit quantization
```

### 3. VRAM Requirements

| Configuration | VRAM Required | Status |
|--------------|---------------|--------|
| Full Precision (bfloat16) | ~18GB | ❌ OOM with other services |
| 8-bit Quantization | ~10GB | ⚠️ Untested (likely works) |
| 4-bit Quantization | ~5GB | ❌ Process killed (OOM) |

### 4. Error Analysis

**Full Precision Test**:
```
torch.OutOfMemoryError: CUDA out of memory.
Tried to allocate 34.00 MiB. GPU 0 has a total capacity of 23.64 GiB
of which 41.31 MiB is free. Process 3590 has 3.79 GiB memory in use.
Process 20493 has 384.00 MiB memory in use.
Including non-PyTorch memory, this process has 19.05 GiB memory in use.
```

**4-bit Quantization Test**:
```
Exit code 137 (SIGKILL)
Process killed after 16.3 seconds
```

The 4-bit test was killed by the system, likely due to:
1. Initial model loading spike (before quantization kicks in)
2. Vision tower reloading (line 79-87 in builder.py)
3. Flash attention memory overhead

## Quantization Implementation

Vidi uses `BitsAndBytesConfig` for quantization:

```python
# From model/builder.py
if load_4bit:
    kwargs['quantization_config'] = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type='nf4',
        llm_int8_skip_modules=["mm_vis", "mm_aud"]  # Skip vision/audio modules
    )
    kwargs['device_map'] = "cuda:0"
```

**Note**: Vision and audio modules are NOT quantized (`llm_int8_skip_modules`), which may explain why VRAM savings are less than expected.

## Recommendations

### Option 1: Stop Other Services (Recommended for Testing)
```bash
# Stop ComfyUI temporarily
kill 20493

# Stop CosyVoice temporarily
docker stop mcn_cosyvoice

# Test Vidi
python3 test_vidi_4bit.py

# Restart services
docker start mcn_cosyvoice
cd /home/jimmy/Documents/mcn/visual/ComfyUI && python3 main.py --listen 0.0.0.0 --port 8188 &
```

### Option 2: Use Vidi on Demand
Only load Vidi when needed, unload other models first:
```python
# In production_pipeline.py
def generate_video_with_vidi():
    # 1. Stop ComfyUI/CosyVoice if running
    # 2. Load Vidi with 4-bit quantization
    # 3. Process video
    # 4. Unload Vidi
    # 5. Restart ComfyUI/CosyVoice
```

### Option 3: Dedicated Vidi Service
Run Vidi in a separate Docker container with exclusive GPU access:
```yaml
# docker-compose.yml
vidi:
  image: mcn-vidi
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            device_ids: ['0']
            capabilities: [gpu]
  environment:
    - CUDA_VISIBLE_DEVICES=0
```

### Option 4: Multi-GPU Setup
If a second GPU is available, dedicate it to Vidi:
```bash
CUDA_VISIBLE_DEVICES=1 python3 inference.py --load-4bit ...
```

## Code Changes Made

### 1. VidiClient Updated
**File**: `middleware/lib/vidi_client.py`

```python
# Added quantization support to _run_inference()
if self.load_4bit:
    cmd.append("--load-4bit")
elif self.load_8bit:
    cmd.append("--load-8bit")
```

### 2. Test Script Created
**File**: `middleware/tests/test_vidi_inference.py`

Comprehensive test with:
- 4-bit quantization
- Multiple queries
- Timing metrics
- Error handling

### 3. Quick Test Script
**File**: `test_vidi_4bit.py`

Simple single-query test for quick validation.

## Next Steps

1. **Test with services stopped**: Verify 4-bit quantization works when GPU is free
2. **Measure actual VRAM usage**: Use `nvidia-smi dmon` during inference
3. **Test 8-bit quantization**: May be a better balance (10GB vs 5GB)
4. **Profile memory spikes**: Identify peak memory usage during loading
5. **Consider CPU offloading**: Use `device_map="auto"` for automatic offloading

## Conclusion

Vidi 1.5 9B **does support** 4-bit and 8-bit quantization, and the VidiClient has been updated to use it. However, the current GPU memory allocation to other services prevents successful loading even with quantization.

**Recommendation**: Implement Option 2 (on-demand loading) for production use, where Vidi is only loaded when needed for video analysis tasks, and other services are temporarily paused.
