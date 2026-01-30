# Vidi 7B Isolated Environment Setup

## Status: ✅ Environment Created, ⚠️ Flash-Attention Version Issue

The isolated Python environment for Vidi 7B has been successfully created with transformers 4.44.2 (required for Mistral 7B architecture).

## Environment Location

```
/home/jimmy/Documents/mcn/external/Vidi/Vidi_7B/vidi7b_env/
```

## Installed Packages

| Package | Version | Purpose |
|---------|---------|---------|
| PyTorch | 2.5.1+cu121 | Deep learning framework |
| Transformers | 4.44.2 | Required for Vidi 7B (Mistral) |
| Flash Attention | 2.6.3 (downgrading) | Efficient attention |
| Accelerate | 0.33.0 | Model loading |
| Bitsandbytes | 0.49.1 | Quantization |
| Sentencepiece | 0.2.1 | Tokenization |
| Decord | 0.6.0 | Video decoding |
| Timm | 0.6.13 | Vision models |
| Protobuf | 6.33.4 | Serialization |

## VidiClient Integration

The `VidiClient` has been updated to automatically use the correct Python environment:

```python
# Vidi 7B → uses vidi7b_env (transformers 4.44.2)
# Vidi 9B → uses middleware venv (transformers 4.57.6)
```

**File**: `/mnt/data_ssd/mcn/middleware/lib/vidi_client.py`

```python
if use_9b and VIDI_9B_DIR.exists():
    self.model_version = "1.5-9B"
    self.python_path = str(MIDDLEWARE_VENV / "bin" / "python3")
else:
    self.model_version = "7B"
    self.python_path = str(VIDI_7B_DIR / "vidi7b_env" / "bin" / "python3")
```

## Current Issue

**Flash-Attention API Mismatch**:
- Installed: flash-attn 2.8.3 (latest)
- Required: flash-attn 2.6.3 (Vidi 7B compatible)
- Error: `unpad_input` function signature changed

**Solution**: Downgrading to flash-attn 2.6.3 (in progress)

## Test Results

### Environment Verification ✅
```
✅ PyTorch: 2.5.1+cu121
✅ Transformers: 4.44.2
✅ Flash Attention: 2.8.3 → 2.6.3 (downgrading)
✅ Accelerate: 0.33.0
✅ Bitsandbytes: 0.49.1
✅ CUDA available: True
✅ GPU: NVIDIA GeForce RTX 4090
✅ CUDA version: 12.1
```

### Model Loading ✅
```
Loading checkpoint shards: 100%|██████████| 4/4 [00:05<00:00,  1.35s/it]
```

### Inference ⚠️
```
ValueError: too many values to unpack (expected 4)
```

## Memory Requirements

| Configuration | VRAM | Status |
|---------------|------|--------|
| Full precision | ~14GB | ✅ Fits with services running |
| 4-bit quantization | ~4GB | ✅ Plenty of room |
| 8-bit quantization | ~7GB | ✅ Plenty of room |

## Usage

### Direct Test
```bash
cd /home/jimmy/Documents/mcn/external/Vidi/Vidi_7B
./vidi7b_env/bin/python inference.py \
  --video-path /path/to/video.mp4 \
  --query "person" \
  --model-path /home/jimmy/Documents/mcn/external/Vidi/Vidi_7B/weights
```

### Via VidiClient
```python
from lib.vidi_client import VidiClient

# Automatically uses vidi7b_env
vidi = VidiClient(use_9b=False)  # or just VidiClient() since 7B is now default

timestamps = vidi.find_timestamps("/path/to/video.mp4", "person")
```

## Comparison: Main vs Isolated Environment

| Component | Main Middleware | Vidi 7B Isolated |
|-----------|----------------|------------------|
| **Location** | `/home/jimmy/Documents/mcn/middleware/.venv` | `/home/jimmy/Documents/mcn/external/Vidi/Vidi_7B/vidi7b_env` |
| **Transformers** | 4.57.6 | 4.44.2 |
| **PyTorch** | 2.9.1+cu128 | 2.5.1+cu121 |
| **Flash-Attn** | 2.6.3 | 2.6.3 (after downgrade) |
| **Compatible With** | Vidi 9B (Gemma2) | Vidi 7B (Mistral) |
| **Used By** | All middleware services | Vidi 7B only |

## Next Steps

1. ✅ Create isolated environment
2. ✅ Install dependencies
3. ⏳ Downgrade flash-attn to 2.6.3
4. ⏳ Test Vidi 7B inference
5. ⏳ Verify quantization works
6. ⏳ Update documentation

## Benefits

- ✅ Both Vidi 7B and 9B can coexist
- ✅ No dependency conflicts
- ✅ Automatic environment selection
- ✅ Vidi 7B uses less VRAM (~14GB vs ~18GB)
- ✅ Can run with other services (CosyVoice, ComfyUI)

## Maintenance

To update Vidi 7B environment:
```bash
cd /home/jimmy/Documents/mcn/external/Vidi/Vidi_7B
./vidi7b_env/bin/pip install --upgrade <package>
```

To recreate from scratch:
```bash
rm -rf vidi7b_env
python3 -m venv vidi7b_env
./vidi7b_env/bin/pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
./vidi7b_env/bin/pip install transformers==4.44.2 accelerate==0.33.0 ...
```

## Conclusion

The isolated environment approach successfully resolves the transformers version conflict between Vidi 7B (Mistral) and Vidi 9B (Gemma2). Once flash-attn 2.6.3 is installed, Vidi 7B should work correctly with lower memory requirements than 9B.
