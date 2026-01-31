# GPU Manager V2 - Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         GPU Resource Manager V2                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐   │
│  │  Service         │  │  VRAM            │  │  Pipeline Phase      │   │
│  │  Registry        │  │  Tracker         │  │  Orchestrator        │   │
│  │                  │  │  (pynvml)        │  │                      │   │
│  │  - Configs       │  │  - Real-time MB  │  │  - Phase → Services  │   │
│  │  - Start/Stop    │  │  - Processes     │  │  - Auto preemption   │   │
│  │  - Health URLs   │  │  - Temperature   │  │  - VRAM budgeting    │   │
│  └────────┬─────────┘  └────────┬─────────┘  └──────────┬───────────┘   │
│           │                     │                       │               │
│           └──────────────┬──────┴───────────────────────┘               │
│                          │                                               │
│                  ┌───────▼───────┐                                      │
│                  │   Lifecycle   │                                      │
│                  │   Manager     │                                      │
│                  │               │                                      │
│                  │  - Docker API │                                      │
│                  │  - subprocess │                                      │
│                  │  - httpx      │                                      │
│                  └───────┬───────┘                                      │
│                          │                                               │
│      ┌───────────────────┼───────────────────┐                          │
│      │                   │                   │                          │
│      ▼                   ▼                   ▼                          │
│  ┌────────┐         ┌────────┐          ┌────────┐                      │
│  │ Docker │         │ Native │          │ Health │                      │
│  │ Driver │         │ Driver │          │ Checks │                      │
│  └────────┘         └────────┘          └────────┘                      │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
            │                   │                   │
            ▼                   ▼                   ▼
       ┌─────────┐        ┌─────────┐         ┌─────────┐
       │CosyVoice│        │ ComfyUI │         │ Vidi 7B │
       │ (Docker)│        │ (Native)│         │ (Native)│
       └─────────┘        └─────────┘         └─────────┘
```

## Component Details

### 1. VRAM Tracker (`lib/vram_tracker.py`)

**Purpose**: Real-time GPU memory monitoring via NVIDIA Management Library (pynvml).

**Responsibilities**:
- Query total/used/free VRAM
- List GPU processes with memory usage
- Check if required VRAM can fit
- Report temperature and utilization

**Interface**:
```python
class VRAMTracker:
    def get_status(self) -> VRAMStatus
    def can_fit(self, required_mb: int) -> bool
    def shutdown(self) -> None
```

**Dependencies**: `pynvml>=11.5.0`

### 2. Service Registry (`lib/service_registry.py`)

**Purpose**: Configuration store for all GPU services.

**Responsibilities**:
- Define service metadata (type, VRAM, priority)
- Store start/stop commands
- Define health check endpoints
- Map services to pipeline phases

**Data Structure**:
```python
@dataclass
class ServiceConfig:
    name: str
    type: ServiceType  # DOCKER | NATIVE
    vram_mb: int
    priority: int
    health_endpoint: str
    health_timeout: int
    warm_time: int
    pipeline_phases: List[int]

    # Docker-specific
    container_name: Optional[str]

    # Native-specific
    start_cmd: Optional[str]
    stop_cmd: Optional[str]
```

### 3. Lifecycle Manager (`lib/lifecycle_manager.py`)

**Purpose**: Start, stop, and monitor GPU services.

**Responsibilities**:
- Start Docker containers via Docker SDK
- Stop Docker containers gracefully
- Start native processes via subprocess
- Stop native processes via pkill
- Health check via HTTP endpoints
- Wait for service ready with timeout

**Interface**:
```python
class LifecycleManager:
    async def ensure_service(self, name: str) -> bool
    async def stop_service(self, name: str, force: bool = False) -> bool
    async def check_health(self, name: str) -> bool
    async def wait_for_health(self, name: str, timeout: int) -> bool
    async def get_all_states(self) -> Dict[str, ServiceState]
```

**Dependencies**: `docker>=6.0.0`, `httpx>=0.24.0`

### 4. GPU Manager V2 (`lib/gpu_manager_v2.py`)

**Purpose**: Unified GPU resource management with pipeline awareness.

**Responsibilities**:
- Integrate VRAM tracker and lifecycle manager
- Implement phase-based orchestration
- Priority-based service preemption
- Redis-based distributed locking
- Provide async context manager for service use

**Interface**:
```python
class GPUManagerV2:
    def get_vram_status(self) -> VRAMStatus
    def get_available_vram(self) -> int
    async def prepare_for_phase(self, phase: int) -> bool
    async def use_service(self, name: str) -> AsyncContextManager[bool]
    async def get_status(self) -> Dict
```

## Data Flow

### Phase Transition Flow

```
User/n8n calls: POST /gpu/prepare-phase/4

    │
    ▼
┌───────────────────────────────────────┐
│  1. Get required services for phase 4 │
│     → ["comfyui"]                     │
└───────────────────────────────────────┘
    │
    ▼
┌───────────────────────────────────────┐
│  2. Get currently running services    │
│     → ["cosyvoice", "vidi"]           │
└───────────────────────────────────────┘
    │
    ▼
┌───────────────────────────────────────┐
│  3. Calculate VRAM budget             │
│     Need: 20 GB                       │
│     Have: 24 - 4 - 4 = 16 GB (short!) │
└───────────────────────────────────────┘
    │
    ▼
┌───────────────────────────────────────┐
│  4. Stop lower-priority services      │
│     Stop vidi (priority 40)           │
│     Stop cosyvoice (priority 50)      │
│     Wait for VRAM reclaim             │
└───────────────────────────────────────┘
    │
    ▼
┌───────────────────────────────────────┐
│  5. Start required services           │
│     Start comfyui                     │
│     Wait for health check             │
└───────────────────────────────────────┘
    │
    ▼
┌───────────────────────────────────────┐
│  6. Return success                    │
│     → {"success": true, "phase": 4}   │
└───────────────────────────────────────┘
```

### Service Start Flow

```
ensure_service("comfyui")
    │
    ├─── Check if already healthy ───────────────── YES ──→ Return True
    │                                    │
    │                                    NO
    │                                    ▼
    ├─── Check VRAM available ─── NO ──→ Preempt lower priority
    │                      │
    │                     YES
    │                      ▼
    ├─── Type == DOCKER? ─── YES ──→ docker.start(container)
    │           │
    │           NO (Native)
    │           ▼
    ├─── subprocess.Popen(start_cmd)
    │
    ▼
    Wait for health check (timeout: 120s)
    │
    ├─── Healthy? ─── YES ──→ Return True
    │       │
    │       NO
    │       ▼
    └─── Log error, Return False
```

## File Structure

```
middleware/
├── lib/
│   ├── gpu_manager.py          # Existing (keep for compatibility)
│   ├── vram_tracker.py         # NEW: VRAM monitoring
│   ├── service_registry.py     # NEW: Service configurations
│   ├── lifecycle_manager.py    # NEW: Start/stop services
│   └── gpu_manager_v2.py       # NEW: Unified manager
├── server.py                   # Add /gpu/* endpoints
├── worker.py                   # Integrate GPU Manager V2
└── tests/
    └── test_gpu_manager_v2.py  # NEW: Comprehensive tests
```

## Integration Points

### Worker Integration

```python
# worker.py - Before
async def process_comfy(task_id, params):
    with gpu_manager.acquire_gpu("comfyui", evict_ollama=True):
        files = comfy_driver.execute_workflow(...)

# worker.py - After
async def process_comfy(task_id, params):
    async with gpu_manager_v2.use_service("comfyui") as ready:
        if not ready:
            raise RuntimeError("Failed to acquire ComfyUI")
        files = comfy_driver.execute_workflow(...)
```

### Server Integration

```python
# server.py - Add endpoints
@app.get("/gpu/status")
async def get_gpu_status():
    return await gpu_manager_v2.get_status()

@app.post("/gpu/prepare-phase/{phase}")
async def prepare_phase(phase: int):
    success = await gpu_manager_v2.prepare_for_phase(phase)
    return {"success": success, "phase": phase}
```

### n8n Integration

```
HTTP Request Node:
  Method: POST
  URL: http://mcn_core:8000/gpu/prepare-phase/4

  → Response: {"success": true, "phase": 4}

  IF success == true:
    → Proceed with ComfyUI workflow
  ELSE:
    → Error handling
```

## Error Handling

| Error | Cause | Recovery |
|-------|-------|----------|
| `ServiceStartTimeout` | Service didn't become healthy | Log, return False, allow retry |
| `InsufficientVRAM` | Can't free enough VRAM | Log, list blocking services |
| `LockTimeout` | Redis lock held too long | TTL auto-release, health check |
| `DockerNotFound` | Container doesn't exist | Log error, suggest docker-compose |
| `HealthCheckFailed` | Service unhealthy | Retry 3x, then give up |
