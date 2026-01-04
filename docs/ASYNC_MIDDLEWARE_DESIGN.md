# Async Middleware Architecture (V8.0) [IMPLEMENTED]
> **Status**: Implemented in Phase 6. Superseded by `MASTER_ARCHITECTURE.md`.

## Overview
Transitions the GPU Middleware from a "Fire-and-Forget" in-memory task runner to a robust "Producer-Consumer" queue system using Redis. This prevents n8n HTTP timeouts and allows precise GPU resource management.

## Components

### 1. The Queue (Redis)
- **Lists**: `gpu_queue:vip` (Priority 100), `gpu_queue:normal` (Priority 10).
- **Data**: JSON strings containing `{id, type, params, status}`.

### 2. The API (`server.py`) -> PRODUCER
- **Role**: Receives HTTP `POST /submit`.
- **Action**: Pushes task to Redis `queued`. Returns `task_id` immediately.
- **Role**: Receives HTTP `GET /status/{id}`.
- **Action**: Checks Redis for job status.

### 3. The Worker (`worker.py`) -> CONSUMER
- **Role**: Dedicated process loop.
- **Action**:
    1. `BLPOP` from VIP, then Normal queues.
    2. Updates status to `processing`.
    3. **Purges VRAM** (ComfyUI / CosyVoice).
    4. Executes Task (Blocking).
    5. Updates status to `completed` with output paths.
    
### 4. Logic Updates
- **ComfyUI**: Use Websocket (WS) for real-time progress monitoring (better than polling).
- **CosyVoice**: Integrate into the same worker loop (Mutual Exclusion with ComfyUI is automatic since worker is single-threaded).

## File Structure Changes
```text
middleware/
├── server.py           (Refactored Producer)
├── worker.py           (New Consumer)
├── lib/
│   ├── redis_client.py (Queue Ops)
│   ├── comfy_driver.py (GPU Ops - Comfy)
│   └── cosy_driver.py  (GPU Ops - Cosy - Wraps existing client)
```
