# Phase 4: Worker Integration

**Risk Level**: High
**Dependencies**: Phase 1, 2, 3 complete
**Estimated Effort**: 1 day

## Overview

Integrate GPU Manager V2 into the existing worker and FastAPI server.

## Prerequisites

- All previous phases complete and verified
- Worker and server running in Docker (`mcn_core`)

## Step 4.1: Add FastAPI Endpoints

**File**: `middleware/server.py`

**Add these imports at the top:**
```python
from lib.gpu_manager_v2 import get_gpu_manager_v2
```

**Add these endpoints:**
```python
# =============================================================================
# GPU Management Endpoints
# =============================================================================

@app.get("/gpu/status")
async def get_gpu_status():
    """
    Get comprehensive GPU status.

    Returns:
        VRAM usage, service states, lock info
    """
    manager = get_gpu_manager_v2()
    return await manager.get_status()


@app.post("/gpu/prepare-phase/{phase}")
async def prepare_gpu_phase(phase: int):
    """
    Prepare GPU for a pipeline phase.

    Automatically stops unnecessary services and starts required ones.

    Args:
        phase: Pipeline phase (1=crawl, 2=analysis, 3=tts, 4=video, 5=render)

    Returns:
        Success status
    """
    if phase < 1 or phase > 5:
        raise HTTPException(400, f"Invalid phase: {phase}. Must be 1-5.")

    manager = get_gpu_manager_v2()
    success = await manager.prepare_for_phase(phase)
    return {"success": success, "phase": phase}


@app.post("/gpu/service/{service_name}/start")
async def start_gpu_service(service_name: str):
    """
    Start a GPU service.

    Args:
        service_name: One of: comfyui, cosyvoice, vidi, ollama

    Returns:
        Success status
    """
    manager = get_gpu_manager_v2()
    if service_name not in manager.services:
        raise HTTPException(404, f"Unknown service: {service_name}")

    success = await manager.lifecycle.ensure_service(service_name)
    return {"success": success, "service": service_name}


@app.post("/gpu/service/{service_name}/stop")
async def stop_gpu_service(service_name: str, force: bool = False):
    """
    Stop a GPU service.

    Args:
        service_name: Service to stop
        force: If true, force kill

    Returns:
        Success status
    """
    manager = get_gpu_manager_v2()
    if service_name not in manager.services:
        raise HTTPException(404, f"Unknown service: {service_name}")

    success = await manager.lifecycle.stop_service(service_name, force)
    return {"success": success, "service": service_name}


@app.post("/gpu/release-all")
async def release_all_gpu_services():
    """Stop all GPU services to free VRAM."""
    manager = get_gpu_manager_v2()
    await manager.release_all()
    return {"success": True, "message": "All GPU services stopped"}


@app.post("/gpu/lock/release")
async def force_release_gpu_lock():
    """Force release GPU lock (use with caution)."""
    manager = get_gpu_manager_v2()
    released = manager.force_release_lock()
    return {"released": released}
```

## Step 4.2: Update Worker for ComfyUI Tasks

**File**: `middleware/worker.py`

**Find the existing `process_comfy` function and update it:**

```python
# Add import
from lib.gpu_manager_v2 import get_gpu_manager_v2

# Replace process_comfy with:
async def process_comfy(task_id: str, params: dict) -> dict:
    """
    Handle ComfyUI task with GPU Manager V2.

    Automatically:
    - Stops other GPU services if needed
    - Acquires GPU lock
    - Starts ComfyUI if not running
    - Executes workflow
    - Releases lock (keeps ComfyUI running)
    """
    gpu_manager = get_gpu_manager_v2()

    async with gpu_manager.use_service("comfyui") as ready:
        if not ready:
            raise RuntimeError(
                "Failed to acquire ComfyUI. "
                f"GPU may be locked by: {gpu_manager.get_lock_holder()}"
            )

        template_name = params.get("template")
        if not template_name:
            raise ValueError("Task params missing 'template'")

        injection_params = params.get("params", {})

        logger.info(f"Executing ComfyUI workflow: {template_name}")
        files = comfy_driver.execute_workflow(template_name, injection_params)

        return {"files": files, "template": template_name}
```

## Step 4.3: Update Worker for Media Analysis Tasks

**File**: `middleware/worker.py`

**Add phase preparation before analysis:**

```python
async def process_media_analysis(task_id: str, params: dict) -> dict:
    """
    Handle media analysis task with Vidi.

    Automatically prepares GPU for analysis phase.
    """
    gpu_manager = get_gpu_manager_v2()

    # Prepare GPU for Phase 2 (Analysis)
    logger.info("Preparing GPU for analysis phase")
    if not await gpu_manager.prepare_for_phase(2):
        logger.warning("Could not prepare GPU for analysis, proceeding anyway")

    # ... rest of existing analysis code ...
```

## Step 4.4: Add GPU Status to Health Endpoint

**File**: `middleware/server.py`

**Update existing `/health` endpoint:**

```python
@app.get("/health")
async def health_check():
    """Health check with GPU status."""
    manager = get_gpu_manager_v2()

    try:
        vram = manager.get_vram_status()
        gpu_ok = vram.free_mb > 1000  # At least 1GB free
    except Exception as e:
        logger.warning(f"GPU health check failed: {e}")
        gpu_ok = False

    return {
        "status": "healthy",
        "gpu": {
            "ok": gpu_ok,
            "free_mb": vram.free_mb if gpu_ok else None,
        },
        "redis": redis_client.ping(),
    }
```

## Verification Checklist

```bash
# 1. Restart the middleware to pick up changes
docker restart mcn_core

# 2. Test GPU status endpoint
curl -s http://localhost:8000/gpu/status | jq

# Expected output:
# {
#   "vram": {"total_mb": 24576, "used_mb": ..., "free_mb": ...},
#   "services": {"comfyui": {"state": "..."}, ...},
#   "lock": {"holder": null, "ttl": -2}
# }

# 3. Test phase preparation
curl -X POST http://localhost:8000/gpu/prepare-phase/4 | jq
# Should return: {"success": true, "phase": 4}

# 4. Verify ComfyUI started
curl -s http://localhost:8188/system_stats | jq '.system.python_version'

# 5. Test service control
curl -X POST http://localhost:8000/gpu/service/cosyvoice/start | jq
curl -X POST http://localhost:8000/gpu/service/cosyvoice/stop | jq

# 6. Submit a ComfyUI task and verify it uses GPU Manager
curl -X POST http://localhost:8000/task/submit \
  -H "Content-Type: application/json" \
  -d '{"type": "comfy", "params": {"template": "test_workflow"}}'
```

## Success Criteria

- [ ] `/gpu/status` returns valid JSON
- [ ] `/gpu/prepare-phase/4` starts ComfyUI
- [ ] `/gpu/prepare-phase/3` starts CosyVoice (stops ComfyUI)
- [ ] `/gpu/service/{name}/start` and `/stop` work
- [ ] Worker acquires GPU lock for ComfyUI tasks
- [ ] No OOM errors during normal pipeline operation

## Rollback Plan

If issues occur, revert to original behavior:

```python
# In worker.py, temporarily disable GPU Manager:
async def process_comfy(task_id: str, params: dict) -> dict:
    # ROLLBACK: Use old behavior
    from lib.gpu_manager import get_gpu_manager
    with get_gpu_manager().acquire_gpu("comfyui", evict_ollama=True):
        # ... original code ...
```

## Next Step

Once Phase 4 is verified, proceed to [07-PHASE5-TESTING.md](./07-PHASE5-TESTING.md).
