# Vidi 7B vs 9B Analysis

## Summary

**Recommendation: Stick with Vidi 1.5 9B** despite memory constraints. Vidi 7B has incompatible dependencies.

## Key Findings

### 1. Dependency Conflict

| Component | Vidi 7B | Vidi 9B | Current |
|-----------|---------|---------|---------|
| Transformers | 4.44.2 | 4.57.6+ | 4.57.6 |
| Accelerate | 0.33.0 | Latest | Latest |
| Architecture | Mistral 7B | Gemma 2 9B | - |

**Problem**: Vidi 7B uses `MistralFlashAttention2` which was removed in transformers 4.45+. Downgrading would break Vidi 9B.

### 2. Model Comparison

| Feature | Vidi 7B | Vidi 1.5 9B |
|---------|---------|-------------|
| **Base Model** | Mistral 7B | Gemma 2 9B |
| **Parameters** | 7B | 9B |
| **VRAM (full)** | ~14GB | ~18GB |
| **VRAM (4-bit)** | ~4GB | ~5GB |
| **Temporal Retrieval** | ✅ | ✅ |
| **Video QA** | ✅ | ✅ |
| **Auto Highlights** | ❌ | ✅ (NEW) |
| **Spatio-temporal Grounding** | ❌ | ✅ (NEW) |
| **Transformers Version** | 4.44.2 | 4.57.6+ |
| **Status** | Legacy | Current |

### 3. Memory Analysis

**Your System**: RTX 4090 24GB

**Current Usage**:
- CosyVoice: 3.8GB
- ComfyUI: 0.4GB
- **Available**: 19.6GB

**Vidi Requirements**:

| Configuration | 7B | 9B | Fits? |
|---------------|----|----|-------|
| Full precision | 14GB | 18GB | ⚠️ Tight |
| + Inference overhead | +2-4GB | +2-4GB | ❌ No |
| **Total** | **16-18GB** | **20-22GB** | ❌ No |
| **With services stopped** | **16-18GB** | **20-22GB** | ✅ Yes (24GB) |
| **4-bit quantized** | **4GB** | **5GB** | ✅ Yes |
| **8-bit quantized** | **7GB** | **9GB** | ✅ Yes |

### 4. Quantization Status

**Vidi 9B**:
- ✅ Supports 4-bit and 8-bit quantization
- ❌ Has dtype mismatch bug (vision tower quantization issue)
- ⚠️ Needs vision/audio modules excluded from quantization
- ⚠️ `llm_int8_skip_modules` causes OOM (keeps modules in full precision)

**Vidi 7B**:
- ✅ Supports 4-bit and 8-bit quantization (in theory)
- ❌ Cannot test due to transformers incompatibility
- ❓ Unknown if has same dtype issues

### 5. Solutions

#### Option 1: Fix Vidi 9B Quantization (Recommended)
**Status**: In progress, dtype mismatch issue

**Problem**: Vision tower (SigLIP) gets quantized but doesn't support quantized inference
- Error: `RuntimeError: self and mat2 must have the same dtype, but got Half and Byte`

**Potential Fixes**:
1. Patch SigLIP to handle quantized weights
2. Load vision/audio towers separately in float16
3. Use custom quantization config that truly skips vision/audio
4. Modify inference.py to cast inputs properly

#### Option 2: Use Vidi 9B Without Quantization
**Status**: Requires stopping other services

**Steps**:
```bash
# Stop services
docker stop mcn_cosyvoice
kill 20493  # ComfyUI

# Run Vidi
python3 test_vidi_9b.py

# Restart services
docker start mcn_cosyvoice
cd /home/jimmy/Documents/mcn/visual/ComfyUI && python3 main.py --listen 0.0.0.0 --port 8188 &
```

**Pros**: Should work immediately
**Cons**: Manual service management, no concurrent use

#### Option 3: Separate Vidi Environment
**Status**: Not implemented

Create isolated environment for Vidi 7B with old transformers:
```bash
python3 -m venv vidi7b_env
source vidi7b_env/bin/activate
pip install transformers==4.44.2 accelerate==0.33.0 ...
```

**Pros**: Both versions available
**Cons**: Maintenance overhead, separate dependencies

#### Option 4: Patch Vidi 7B for New Transformers
**Status**: Requires code changes

Update `Vidi_7B/model/lmm/dattn/mistral.py` to use new transformers API:
- Replace `MistralFlashAttention2` with `MistralAttention`
- Update attention mechanism calls
- Test compatibility

**Pros**: Single environment
**Cons**: Significant code changes, may break functionality

### 6. Recommendation

**Short-term**: Use Vidi 9B without quantization, stop services when needed

**Medium-term**: Fix Vidi 9B quantization dtype issue
- Investigate why `llm_int8_skip_modules` doesn't work properly
- Consider loading vision/audio towers separately
- Test with different bitsandbytes versions

**Long-term**: Consider upgrading to newer Vidi releases or alternative models

### 7. Test Results

#### Vidi 9B (Full Precision)
- ✅ Model loads successfully
- ❌ OOM during inference with other services running
- ✅ Should work with services stopped (untested)

#### Vidi 9B (4-bit Quantization)
- ✅ Model loads successfully (18s)
- ❌ Dtype mismatch during inference
- ❌ OOM when skipping vision/audio from quantization

#### Vidi 7B
- ❌ Import error: `MistralFlashAttention2` not found
- ❌ Incompatible with transformers 4.57.6
- ⚠️ Requires transformers 4.44.2 (breaks Vidi 9B)

### 8. Next Steps

1. **Test Vidi 9B without quantization** (stop services first)
2. **Debug quantization dtype issue** (vision tower handling)
3. **Consider on-demand loading** (load Vidi only when needed)
4. **Evaluate alternative models** (if Vidi proves too memory-intensive)

## Conclusion

Vidi 7B is not a viable option due to dependency conflicts. Focus on making Vidi 9B work either:
- Without quantization (requires stopping other services)
- With fixed quantization (requires debugging dtype issues)

The memory is available (24GB), but concurrent service usage and quantization bugs are the blockers.
