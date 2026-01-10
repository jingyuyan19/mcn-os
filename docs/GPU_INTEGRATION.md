# GPU Integration Guide

**Purpose:** ComfyUI, CosyVoice, and WanVideo configuration  
**Updated:** 2026-01-07

---

## CosyVoice v3 (Golden Environment) ✅

### Docker Container
```yaml
# docker-compose.yml
cosyvoice:
  image: cosyvoice:v3-vpn
  ports:
    - "50000:50000"
  volumes:
    - ./assets/pretrained_models:/models:ro
    - cosyvoice_cache:/root/.cache/modelscope
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

### API: Zero-Shot Voice Cloning
```bash
POST http://localhost:50000/inference_zero_shot
Content-Type: multipart/form-data

# Parameters:
# - tts_text: Text to synthesize (must include <|endofprompt|> for CosyVoice3)
# - prompt_text: Reference prompt (format: "You are a helpful assistant.<|endofprompt|>参考文本")
# - prompt_wav: Reference audio file (binary upload)
```

### Example (Python)
```python
import requests

files = {
    'tts_text': (None, '<|endofprompt|>要合成的文字内容'),
    'prompt_text': (None, 'You are a helpful assistant.<|endofprompt|>希望你以后能够做的比我还好呦。'),
    'prompt_wav': ('prompt.wav', open('reference.wav', 'rb'), 'audio/wav')
}

response = requests.post('http://localhost:50000/inference_zero_shot', files=files)
# Returns raw PCM audio (16-bit signed, 24kHz, mono)
```

### Output Format
The API returns **raw PCM data** (not WAV with headers). To convert:
```bash
ffmpeg -f s16le -ar 24000 -ac 1 -i input.raw -y output.wav
```

### Verified Working (2026-01-07)
| Test | Result |
|------|--------|
| English TTS | ✅ 211KB, 2.80s |
| Chinese TTS | ✅ 351KB, 2.85s |
| Trembling | ✅ **FIXED** |

---

## ComfyUI Setup

### Location
```
/mnt/data_ssd/ComfyUI/
```

### Start Script
```bash
./start_comfy.sh
# Opens http://localhost:8188
```

### Custom Nodes
| Node | Purpose |
|------|---------|
| ComfyUI-Manager | Package manager |
| WAN-Video | Video generation |
| LongCat | Avatar lip-sync |
| LoRA Stack | Multiple LoRA loading |

---

## Model Structure

```
models/
├── checkpoints/
│   ├── flux_dev_bf16.safetensors
│   └── wan2.1_t2v_1.3b_bf16.safetensors
├── vae/
│   └── flux_vae.safetensors
├── text_encoders/
│   ├── t5xxl_fp16.safetensors
│   └── clip_l.safetensors
├── loras/
│   └── longcat_lora.safetensors
└── unet/
    └── wan_unet_bf16.safetensors
```

---

## Workflow Templates

**Location:** `middleware/workflows/`

| Template | Purpose |
|----------|---------|
| `flux_dev.json` | Image generation |
| `wan_t2v.json` | Text-to-video |
| `wan_i2v.json` | Image-to-video |
| `longcat_avatar.json` | Lip-sync avatar |

### Template Injection
The middleware replaces `{{VARIABLE}}` placeholders:

```json
{
  "inputs": {
    "text": "{{POSITIVE_PROMPT}}",
    "seed": "{{SEED}}"
  }
}
```

---

## VRAM Management

| Model | VRAM Required |
|-------|---------------|
| Flux Dev (bf16) | ~12GB |
| WanVideo 1.3B | ~8GB |
| WanVideo 14B | ~24GB |
| CosyVoice v3 | ~4GB |

### GPU Lock
The middleware uses distributed locking to prevent VRAM conflicts:

```python
# middleware/lock_manager.py
with gpu_lock:
    run_comfyui_workflow()
```

---

## API Integration

### ComfyUI WebSocket
```python
# middleware/lib/comfy_driver.py
async def execute_workflow(template, params):
    # 1. Load template JSON
    # 2. Inject params
    # 3. Queue to ComfyUI WebSocket
    # 4. Wait for completion
    # 5. Return output path
```

### CosyVoice Client
```python
# middleware/cosyvoice_client.py
async def generate_speech(text, prompt_text, prompt_wav_path):
    # 1. Call /inference_zero_shot
    # 2. Convert PCM to WAV
    # 3. Return audio path
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "CUDA out of memory" | Close browser tabs, restart ComfyUI |
| "Model not found" | Check `models/` path in ComfyUI settings |
| "WebSocket timeout" | Increase timeout, check ComfyUI is running |
| "Black output" | Model loading failed, check console |
| **CosyVoice trembling** | Use `cosyvoice:v3-vpn` image ✅ |
| CosyVoice "Invalid file" | Ensure temp file is flushed before reading |
| CosyVoice wrong class | Remove `cosyvoice.yaml` symlink, keep only `cosyvoice3.yaml` |
