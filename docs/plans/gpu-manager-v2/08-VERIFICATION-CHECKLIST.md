# GPU Manager V2 - Verification Checklist

## Overview

This document provides a step-by-step verification guide for the GPU Manager V2 implementation. Complete each phase before proceeding to the next.

---

## Pre-Flight Checks

Before starting implementation, verify the environment:

```bash
# 1. GPU is accessible
nvidia-smi
# Expected: RTX 4090 with 24GB VRAM

# 2. Docker is running
docker ps
# Expected: mcn_core, mcn_cosyvoice, etc.

# 3. Redis is accessible
docker exec mcn_core redis-cli -h redis -a 123456 ping
# Expected: PONG

# 4. Python venv is available
ls /mnt/data_ssd/mcn/middleware/.venv/bin/python
# Expected: File exists
```

---

## Phase 1: VRAM Tracking

### Implementation

- [ ] Add `pynvml>=11.5.0` to `requirements.txt`
- [ ] Create `middleware/lib/vram_tracker.py`
- [ ] Create `middleware/scripts/test_vram_tracker.py`

### Verification

```bash
cd /mnt/data_ssd/mcn/middleware
source .venv/bin/activate

# Install pynvml
pip install pynvml

# Run verification script
python scripts/test_vram_tracker.py
```

### Expected Output

```
============================================================
VRAM Tracker Test
============================================================

GPU Memory:
  Total:       24,576 MB
  Used:        X,XXX MB
  Free:        XX,XXX MB
  Temperature: XX°C
  Utilization: X%

GPU Processes (N):
  PID XXXXX: X,XXX MB - python3
  ...

Can fit tests:
  ✓ 4,000 MB: YES
  ✓ 10,000 MB: YES
  ✓ 18,000 MB: YES/NO (depends on current usage)
  ✗ 22,000 MB: NO

============================================================
```

### Sign-off

- [ ] VRAM total shows 24,576 MB
- [ ] GPU processes are listed
- [ ] `can_fit()` returns correct results
- [ ] No errors during execution

---

## Phase 2: Lifecycle Manager

### Implementation

- [ ] Add `docker>=6.0.0` and `httpx>=0.24.0` to `requirements.txt`
- [ ] Create `middleware/lib/service_registry.py`
- [ ] Create `middleware/lib/lifecycle_manager.py`
- [ ] Create `middleware/scripts/test_lifecycle_manager.py`

### Verification

```bash
cd /mnt/data_ssd/mcn/middleware
source .venv/bin/activate

# Install dependencies
pip install docker httpx

# Run verification script
python scripts/test_lifecycle_manager.py
```

### Expected Output

```
============================================================
Lifecycle Manager Test
============================================================

Service Health Check:
  🟢 comfyui: ready (priority: 100, vram: 20000 MB)
  🔴 cosyvoice: stopped (priority: 50, vram: 4000 MB)
  🔴 vidi: stopped (priority: 40, vram: 4000 MB)
  🔴 ollama: stopped (priority: 10, vram: 18000 MB)

============================================================
```

### Interactive Test

```bash
# Test starting CosyVoice
python -c "
import asyncio
from lib.lifecycle_manager import get_lifecycle_manager

async def test():
    mgr = get_lifecycle_manager()
    print('Starting CosyVoice...')
    result = await mgr.ensure_service('cosyvoice')
    print(f'Result: {result}')
    print('Stopping CosyVoice...')
    result = await mgr.stop_service('cosyvoice')
    print(f'Result: {result}')

asyncio.run(test())
"
```

### Sign-off

- [ ] All 4 services appear in registry
- [ ] Health checks return correct state
- [ ] Docker services can be started/stopped
- [ ] VRAM is freed after stopping service (verify with `nvidia-smi`)

---

## Phase 3: GPU Manager V2

### Implementation

- [ ] Create `middleware/lib/gpu_manager_v2.py`
- [ ] Create `middleware/scripts/test_gpu_manager_v2.py`

### Verification

```bash
cd /mnt/data_ssd/mcn/middleware
source .venv/bin/activate

# Run verification script
python scripts/test_gpu_manager_v2.py
```

### Expected Output

```
============================================================
GPU Manager V2 Test
============================================================

VRAM Status:
  Total:     24,576 MB
  Used:      X,XXX MB
  Free:      XX,XXX MB
  Available: XX,XXX MB (after reserve)
  Temp:      XX°C

GPU Processes:
  PID XXXXX: X,XXX MB - python3

Services:
  🟢 comfyui: ready | P100 | 20,000 MB | phases: 4
  🔴 cosyvoice: stopped | P50 | 4,000 MB | phases: 3
  🔴 vidi: stopped | P40 | 4,000 MB | phases: 2
  🔴 ollama: stopped | P10 | 18,000 MB | phases: -

Lock:
  Holder: None
  TTL:    -2s

============================================================
```

### Phase Transition Test

```bash
# Test phase 4 (Video Generation)
python -c "
import asyncio
from lib.gpu_manager_v2 import get_gpu_manager_v2

async def test():
    mgr = get_gpu_manager_v2()
    print('Preparing for Phase 4 (Video Generation)...')
    success = await mgr.prepare_for_phase(4)
    print(f'Success: {success}')

    status = await mgr.get_status()
    for name, svc in status['services'].items():
        print(f'  {name}: {svc[\"state\"]}')

asyncio.run(test())
"

# Verify ComfyUI is running
curl -s http://localhost:8188/system_stats | jq '.system.python_version'
```

### Sign-off

- [ ] Status shows all services with correct metadata
- [ ] `prepare_for_phase(4)` starts ComfyUI
- [ ] `prepare_for_phase(3)` stops ComfyUI, starts CosyVoice
- [ ] Redis lock is working (holder shows service name during operation)

---

## Phase 4: Worker Integration

### Implementation

- [ ] Add GPU endpoints to `middleware/server.py`
- [ ] Update `process_comfy` in `middleware/worker.py`
- [ ] Restart middleware: `docker restart mcn_core`

### Verification

```bash
# Test GPU status endpoint
curl -s http://localhost:8000/gpu/status | jq

# Test phase preparation
curl -X POST http://localhost:8000/gpu/prepare-phase/4 | jq

# Test service control
curl -X POST http://localhost:8000/gpu/service/cosyvoice/start | jq
curl -X POST http://localhost:8000/gpu/service/cosyvoice/stop | jq
```

### Expected Output (GPU Status)

```json
{
  "vram": {
    "total_mb": 24576,
    "used_mb": 4000,
    "free_mb": 20576,
    "available_mb": 19552,
    "processes": [...],
    "temperature_c": 45,
    "utilization_percent": 10
  },
  "services": {
    "comfyui": {"state": "ready", "vram_mb": 20000, "priority": 100, "phases": [4]},
    "cosyvoice": {"state": "stopped", "vram_mb": 4000, "priority": 50, "phases": [3]},
    ...
  },
  "lock": {"holder": null, "ttl": -2}
}
```

### Sign-off

- [ ] All API endpoints return valid JSON
- [ ] Phase transitions work via API
- [ ] Service start/stop works via API
- [ ] Worker logs show "GPU locked for comfyui" during tasks

---

## Phase 5: Testing

### Implementation

- [ ] Create `middleware/tests/test_vram_tracker.py`
- [ ] Create `middleware/tests/test_lifecycle_manager.py`
- [ ] Create `middleware/tests/test_gpu_manager_v2.py`

### Verification

```bash
cd /mnt/data_ssd/mcn/middleware
source .venv/bin/activate

# Install test dependencies
pip install pytest pytest-asyncio

# Run all tests
pytest tests/test_vram_tracker.py tests/test_lifecycle_manager.py tests/test_gpu_manager_v2.py -v

# Check coverage
pytest tests/test_gpu_manager_v2.py --cov=lib --cov-report=term-missing
```

### Expected Output

```
tests/test_vram_tracker.py::TestVRAMTracker::test_get_status_returns_valid_data PASSED
tests/test_vram_tracker.py::TestVRAMTracker::test_can_fit_returns_true_when_enough_vram PASSED
...
tests/test_gpu_manager_v2.py::TestGPUManagerV2::test_prepare_for_phase_starts_service PASSED
...

---------- coverage: ... ----------
Name                           Stmts   Miss  Cover
--------------------------------------------------
lib/gpu_manager_v2.py            150     25    83%
lib/lifecycle_manager.py         120     20    83%
lib/vram_tracker.py               60      5    92%
--------------------------------------------------
TOTAL                            330     50    85%
```

### Sign-off

- [ ] All tests pass
- [ ] Coverage is 80%+ for new modules
- [ ] No test failures or errors

---

## End-to-End Verification

### Full Pipeline Test

```bash
# 1. Start fresh (stop all GPU services)
curl -X POST http://localhost:8000/gpu/release-all

# 2. Verify GPU is free
nvidia-smi
# Should show minimal VRAM usage

# 3. Simulate pipeline phases
curl -X POST http://localhost:8000/gpu/prepare-phase/2  # Analysis (Vidi)
sleep 30
curl -s http://localhost:8000/gpu/status | jq '.services.vidi.state'
# Expected: "ready"

curl -X POST http://localhost:8000/gpu/prepare-phase/3  # TTS (CosyVoice)
sleep 15
curl -s http://localhost:8000/gpu/status | jq '.services'
# Expected: vidi=stopped, cosyvoice=ready

curl -X POST http://localhost:8000/gpu/prepare-phase/4  # Video (ComfyUI)
sleep 45
curl -s http://localhost:8000/gpu/status | jq '.services'
# Expected: cosyvoice=stopped, comfyui=ready

# 4. Verify no OOM during LongCat workflow
# Run your LongCat workflow in ComfyUI
```

### Sign-off

- [ ] Phase transitions work end-to-end
- [ ] No OOM errors during workflow execution
- [ ] VRAM is properly managed throughout pipeline

---

## Rollback Procedure

If issues occur, revert to original behavior:

1. **Revert worker.py changes**:
   ```python
   # Use old gpu_manager instead of gpu_manager_v2
   from lib.gpu_manager import get_gpu_manager
   ```

2. **Remove new endpoints from server.py**

3. **Restart middleware**:
   ```bash
   docker restart mcn_core
   ```

4. **Start services manually**:
   ```bash
   docker start mcn_cosyvoice
   ./start_comfy.sh
   ```

---

## Final Checklist

- [ ] Phase 1: VRAM Tracking verified
- [ ] Phase 2: Lifecycle Manager verified
- [ ] Phase 3: GPU Manager V2 verified
- [ ] Phase 4: Worker Integration verified
- [ ] Phase 5: Tests passing with 80%+ coverage
- [ ] End-to-End pipeline test passed
- [ ] No OOM errors during normal operation
- [ ] Documentation updated

**GPU Manager V2 Implementation Complete!**
