# GPU Manager V2 - Requirements

## Problem Analysis

### Current State

The MCN OS pipeline runs on a single RTX 4090 (24GB VRAM) with multiple GPU-intensive services:

```
┌─────────────────────────────────────────────────────────────┐
│                    RTX 4090 (24 GB VRAM)                    │
├─────────────────────────────────────────────────────────────┤
│  ComfyUI+LongCat │  CosyVoice │  Vidi 7B  │  Ollama        │
│     18-20 GB     │    4 GB    │   4 GB    │   18 GB        │
├─────────────────────────────────────────────────────────────┤
│  TOTAL NEEDED: 30-36 GB   │   AVAILABLE: 24 GB             │
│                           │   RESULT: OOM ERRORS           │
└─────────────────────────────────────────────────────────────┘
```

### Root Cause

1. **No VRAM tracking**: System doesn't know actual GPU memory usage
2. **No lifecycle management**: Services started manually, never stopped
3. **No coordination**: Multiple services compete for same VRAM
4. **No priority system**: Low-priority services block high-priority work

### Existing Implementation

Current `middleware/lib/gpu_manager.py` provides:
- ✅ Redis-based mutex lock
- ✅ Ollama model eviction (`keep_alive=0`)
- ❌ No VRAM tracking
- ❌ No Docker service management
- ❌ No native process management
- ❌ No health checks
- ❌ No pipeline phase awareness

## Requirements

### Functional Requirements

#### FR-1: VRAM Monitoring
- **FR-1.1**: Query real-time VRAM usage via pynvml
- **FR-1.2**: List GPU processes with memory consumption
- **FR-1.3**: Provide `can_fit(required_mb)` check
- **FR-1.4**: Include GPU temperature and utilization

#### FR-2: Service Lifecycle
- **FR-2.1**: Start Docker containers (`docker start <name>`)
- **FR-2.2**: Stop Docker containers (`docker stop <name>`)
- **FR-2.3**: Start native processes (shell commands)
- **FR-2.4**: Stop native processes (pkill patterns)
- **FR-2.5**: Health check via HTTP endpoint
- **FR-2.6**: Wait for service ready with timeout

#### FR-3: Pipeline Phase Orchestration
- **FR-3.1**: Define service requirements per phase
- **FR-3.2**: `prepare_for_phase(n)` stops unnecessary, starts required
- **FR-3.3**: Automatic VRAM budget calculation
- **FR-3.4**: Priority-based preemption

#### FR-4: API Endpoints
- **FR-4.1**: `GET /gpu/status` - VRAM and service status
- **FR-4.2**: `POST /gpu/prepare-phase/{n}` - Phase transition
- **FR-4.3**: `POST /gpu/service/{name}/start` - Manual start
- **FR-4.4**: `POST /gpu/service/{name}/stop` - Manual stop

### Non-Functional Requirements

#### NFR-1: Performance
- Health checks complete within 10 seconds
- VRAM queries return within 100ms
- Service start timeout: 120 seconds max
- Service stop timeout: 30 seconds max

#### NFR-2: Reliability
- Redis locks have TTL to prevent deadlocks
- Crash recovery via health check polling
- Graceful degradation if pynvml unavailable

#### NFR-3: Observability
- All operations logged with loguru
- Status endpoint provides full system view
- Error messages include actionable context

## Constraints

### Hardware
- Single GPU: NVIDIA RTX 4090 (24GB)
- Cannot use MIG (not supported on consumer GPUs)
- Desktop GUI consumes ~500-1000 MB baseline

### Software
- Python 3.10+ (async/await)
- Docker for container management
- Redis for distributed locking
- FastAPI for HTTP endpoints

### Operational
- Services are heterogeneous (Docker + native)
- Pipeline phases are sequential (no parallel GPU work)
- Must not break existing `gpu_manager.py` consumers

## Service Inventory

| Service | Type | Container/Process | VRAM | Priority | Health Endpoint | Phases |
|---------|------|-------------------|------|----------|-----------------|--------|
| ComfyUI | Native | `python main.py --listen` | 20 GB | 100 | `localhost:8188/system_stats` | 4 |
| CosyVoice | Docker | `mcn_cosyvoice` | 4 GB | 50 | `localhost:50000/docs` | 3 |
| Vidi 7B | Native | `vidi_server` | 4 GB | 40 | `localhost:8099/health` | 2 |
| Ollama | Docker | `mcn_ollama` | 18 GB | 10 | `localhost:11434/api/tags` | - |

## Acceptance Criteria

### AC-1: OOM Prevention
```bash
# This sequence should NOT cause OOM
curl -X POST localhost:8000/gpu/prepare-phase/2  # Start Vidi
curl -X POST localhost:8000/gpu/prepare-phase/3  # Stop Vidi, Start CosyVoice
curl -X POST localhost:8000/gpu/prepare-phase/4  # Stop CosyVoice, Start ComfyUI
```

### AC-2: Status Visibility
```bash
curl localhost:8000/gpu/status | jq
# Returns:
# {
#   "vram": {"total_mb": 24576, "used_mb": 4000, "free_mb": 20576},
#   "services": {"comfyui": {"state": "ready"}, ...},
#   "lock": {"holder": null}
# }
```

### AC-3: Preemption
```bash
# With CosyVoice running (4GB), requesting ComfyUI (20GB) should:
# 1. Stop CosyVoice automatically
# 2. Wait for VRAM reclamation
# 3. Start ComfyUI
curl -X POST localhost:8000/gpu/service/comfyui/start
```

## Out of Scope

- Multi-GPU support (not needed)
- Remote GPU management (single machine)
- GPU sharing/MPS (services need exclusive access)
- Kubernetes integration (overkill for single machine)
