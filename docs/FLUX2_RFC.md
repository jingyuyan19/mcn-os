# RFC v6: FLUX.2 FP8 Noise - Complete Diagnosis for Deep Think

**Date**: 2025-12-30 23:53  
**Status**: UNSOLVED - All standard fixes exhausted, requesting architecture-level analysis

---

## Problem

FLUX.2 Dev FP8 generates static noise. Fresh model download completed, official workflow tested, all configurations verified correct.

---

## Environment

- **GPU**: NVIDIA RTX 4090 (24GB)
- **ComfyUI**: v0.6.0-15-gd7111e42
- **PyTorch**: 2.9.1+cu128
- **xformers**: DISABLED (using pytorch attention)

---

## Latest Server Log (Verified Execution)

```
Got prompt
Using pytorch attention in VAE
VAE load device: cuda:0, dtype: torch.bfloat16

Found quantization metadata version 1
Using MixedPrecisionOps for text encoder
CLIP/text encoder model load device: cuda:0, dtype: torch.float16

Requested to load Flux2TEModel_
loaded completely; 21855.86 MB usable, 17180.60 MB loaded, full load: True

Found quantization metadata version 1
Detected mixed precision quantization
Using mixed precision operations
model weight dtype torch.bfloat16, manual cast: torch.bfloat16
model_type FLUX

Requested to load Flux2
loaded partially; 20301.26 MB usable, 19440.00 MB loaded, 14373.00 MB offloaded

100%|██████████| 20/20 [00:36<00:00, 1.84s/it]

Prompt executed in 57.23 seconds
```

---

## Model File Verification

```
File: mistral_3_small_flux2_fp8.safetensors
Size: 18,034,640,095 bytes (17GB)
Status: FRESH DOWNLOAD from HuggingFace
Tensor entries: 693
Quantization metadata: ✓ Present
Sample tensor dtype: F32
```

---

## Workflow Verification

Using official **comfyanonymous** workflow from https://comfyanonymous.github.io/ComfyUI_examples/flux2/

```
CLIPLoader: ['mistral_3_small_flux2_fp8.safetensors', 'flux2', 'default']
UNETLoader: ['flux2_dev_fp8mixed.safetensors', 'default']
VAELoader: ['flux2-vae.safetensors']
FluxGuidance: [4]
EmptyFlux2LatentImage: [1024, 1024, 1]
Flux2Scheduler: [20, 1024, 1024]
KSamplerSelect: ['euler']
SamplerCustomAdvanced + BasicGuider + RandomNoise
```

---

## What Has Been Tried

| Attempt | Action | Result |
|---------|--------|--------|
| 1 | Original workflow | Noise |
| 2 | Removed PuLID-Flux | Noise |
| 3 | EmptyFlux2LatentImage (32ch) | Noise |
| 4 | Disabled xformers | Noise |
| 5 | VAE isolation test | **PASSED** (gray) |
| 6 | DualCLIPLoader | Dimension error |
| 7 | Official workflow match | Noise |
| 8 | comfyanonymous workflow | Noise |
| 9 | Fresh model download | Noise |

---

## Key Observations

1. **VAE works** - Isolation test produces gray image
2. **Sampling completes** - 20/20 steps, no errors
3. **Models load** - No loading errors, correct file sizes
4. **Output is consistent noise** - Not random failure

---

## Hypothesis: Mixed Precision Operation Bug?

Log shows:
```
model weight dtype torch.bfloat16, manual cast: torch.bfloat16
```

The FP8 model is being cast to bfloat16 for computation. Could there be a precision/casting issue in the flow matching sampler?

---

## Questions for Deep Think

1. **Is the `manual cast: torch.bfloat16` for FP8 models expected behavior?**
   - Should FP8 stay as F8 or be cast to BF16?

2. **Could `MixedPrecisionOps` be introducing NaN/Inf?**
   - The text encoder uses MixedPrecisionOps

3. **Is there a known issue with PyTorch 2.9.1 + FLUX.2 FP8?**
   - Should we try PyTorch 2.5.x?

4. **Could the problem be in the sigma schedule or noise injection?**
   - Flow matching requires specific sigma handling

5. **Is there a way to verify the FP8 weights are not producing NaN during inference?**
   - Perhaps intermediate tensor debugging?

---

## Suggested Debug Approach

1. Add tensor debugging to capture intermediate values during sampling
2. Test with PyTorch 2.5.1 instead of 2.9.1
3. Try completely different CUDA toolkit version
4. Test same setup on different machine
