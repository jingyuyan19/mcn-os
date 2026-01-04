# GPU Integration Guide

**Purpose:** ComfyUI and WanVideo configuration

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
| LoRA Stack | Multiple LoRA loading |

---

## Model Structure

```
models/
├── checkpoints/
│   ├── flux_dev_bf16.safetensors      # Flux image model
│   └── wan2.1_t2v_1.3b_bf16.safetensors # WanVideo
├── vae/
│   └── flux_vae.safetensors
├── text_encoders/
│   ├── t5xxl_fp16.safetensors
│   └── clip_l.safetensors
├── loras/
│   └── longcat_lora.safetensors       # LongCat avatar
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

### GPU Lock
The middleware uses distributed locking to prevent VRAM conflicts:

```python
# middleware/lock_manager.py
with gpu_lock:
    # Only one task uses GPU at a time
    run_comfyui_workflow()
```

---

## API Integration

### From n8n/Middleware
```python
# middleware/lib/comfy_driver.py
async def execute_workflow(template, params):
    # 1. Load template JSON
    # 2. Inject params
    # 3. Queue to ComfyUI WebSocket
    # 4. Wait for completion
    # 5. Return output path
```

### WebSocket Protocol
```python
ws = websocket.connect('ws://localhost:8188/ws')
ws.send(json.dumps({
    "type": "execute",
    "data": {"prompt": workflow_json}
}))
```

---

## CosyVoice TTS

### Docker Container
```yaml
# docker-compose.yml
cosyvoice:
  image: cosyvoice:v3.0
  ports:
    - "50000:50000"
  volumes:
    - ./assets:/opt/CosyVoice/assets
```

### API
```bash
POST http://localhost:50000/tts

{
  "text": "Script to speak",
  "mode": "instruct",
  "voice_name": "中文女"
}
```

### Voice Cloning
```bash
POST http://localhost:50000/clone

{
  "text": "Clone this voice",
  "reference_audio": "path/to/reference.wav"
}
```

---

## LongCat Digital Human

### Reference
See `docs/longcat_avatar_guide.md` for:
- LoRA training setup
- Character consistency
- Expression control

### Workflow
1. Generate face with Flux + LongCat LoRA
2. Animate with WanVideo i2v
3. Composite in Remotion

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "CUDA out of memory" | Close browser tabs, restart ComfyUI |
| "Model not found" | Check `models/` path in ComfyUI settings |
| "WebSocket timeout" | Increase timeout, check ComfyUI is running |
| "Black output" | Model loading failed, check console |
