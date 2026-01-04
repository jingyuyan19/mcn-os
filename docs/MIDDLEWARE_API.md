# Middleware API Reference

**Location:** `/middleware/`  
**Purpose:** GPU task orchestration and job queue management

---

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  FastAPI Server │────▶│   Redis Queue   │────▶│   GPU Worker    │
│   server.py     │     │   (port 6379)   │     │   worker.py     │
│   (port 8000)   │     └─────────────────┘     └────────┬────────┘
└─────────────────┘                                      │
                                          ┌──────────────┼──────────────┐
                                          ▼              ▼              ▼
                                    ┌──────────┐  ┌──────────┐  ┌──────────┐
                                    │ ComfyUI  │  │CosyVoice │  │ Remotion │
                                    │ Driver   │  │ Client   │  │ Driver   │
                                    └──────────┘  └──────────┘  └──────────┘
```

---

## API Endpoints

### POST `/submit_task`
Submit a GPU task to the queue.

**Request Body:**
```json
{
  "task_type": "comfyui | cosyvoice | remotion_render",
  "priority": 50,           // Higher = processed first
  "payload": { ... }        // Task-specific data
}
```

**Response:**
```json
{
  "status": "queued",
  "task_id": "uuid-v4"
}
```

### GET `/task_status/{task_id}`
Check task status.

**Response:**
```json
{
  "status": "pending | processing | completed | failed",
  "result": { ... }
}
```

---

## Task Types

### `comfyui`
Image/video generation via ComfyUI.

```json
{
  "task_type": "comfyui",
  "payload": {
    "template": "flux_dev | wan_t2v | wan_i2v",
    "params": {
      "POSITIVE_PROMPT": "your prompt",
      "SEED": 12345,
      "STEPS": 20
    }
  }
}
```

**Templates:** Located in `middleware/workflows/`

### `cosyvoice`
Text-to-speech generation.

```json
{
  "task_type": "cosyvoice",
  "payload": {
    "text": "Script to speak",
    "voice_id": "luna",          // Reference voice
    "mode": "instruct | clone",
    "output_path": "audio/output.wav"
  }
}
```

### `remotion_render`
Video composition and rendering.

```json
{
  "task_type": "remotion_render",
  "payload": {
    "timeline": {
      "width": 1080,
      "height": 1920,
      "fps": 30,
      "durationInFrames": 1800,
      "clips": [...],
      "subtitles": [...],
      "audioSrc": "audio/voice.wav",
      "bgmSrc": "audio/bgm.mp3"
    }
  }
}
```

---

## Key Files

| File | Purpose |
|------|---------|
| `server.py` | FastAPI HTTP server |
| `worker.py` | Redis consumer, task router |
| `lib/comfy_driver.py` | ComfyUI WebSocket client |
| `lib/cosyvoice_driver.py` | CosyVoice HTTP client |
| `lib/remotion_driver.py` | Remotion subprocess handler |
| `lock_manager.py` | Distributed lock for single-GPU |

---

## Configuration

**Environment Variables:**
```bash
REDIS_HOST=localhost
REDIS_PORT=6379
COMFYUI_URL=http://localhost:8188
COSYVOICE_URL=http://localhost:50000
ASSET_PATH=/mnt/data_ssd/mcn/assets
```

**Start Commands:**
```bash
# Terminal 1: API Server
cd middleware && python server.py

# Terminal 2: GPU Worker
cd middleware && python worker.py

# Or use the combined script:
./start_middleware.sh
```

---

## Logging

- **Server:** `middleware/server.log`
- **Worker:** `middleware/worker.log`

**Log Format:**
```
2026-01-04 09:32:56,732 - GPUWorker - INFO - ▶️ Processing: remotion_render (ID: abc123)
2026-01-04 09:34:52,083 - GPUWorker - INFO - ✅ Done: remotion_render abc123
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Connection refused" | Start Redis: `docker compose up redis -d` |
| "VRAM exhausted" | Wait for current task, or restart ComfyUI |
| "Render failed" | Check `worker.log` for Remotion errors |
| "Template not found" | Verify workflow JSON in `middleware/workflows/` |
