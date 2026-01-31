# GPU Manager V2 - Implementation Plan

**Version**: 1.0
**Created**: 2026-02-01
**Status**: Planning
**Owner**: MCN OS Team

## Problem Statement

MCN OS runs multiple GPU-intensive AI services on a single RTX 4090 (24GB):
- **ComfyUI + LongCat**: ~18-20 GB (video generation)
- **CosyVoice**: ~4 GB (TTS, Docker)
- **Vidi 7B**: ~4 GB (video understanding, native)
- **Ollama**: ~4-8 GB (LLM fallback, Docker)

**Total required**: ~30-36 GB
**Available**: 24 GB
**Result**: OOM errors when services run simultaneously

## Solution

A lightweight, custom GPU resource manager that:
1. Tracks real-time VRAM usage via pynvml
2. Manages service lifecycle (start/stop Docker & native processes)
3. Orchestrates services based on pipeline phase
4. Preempts lower-priority services when needed

## Document Index

| Document | Description |
|----------|-------------|
| [01-REQUIREMENTS.md](./01-REQUIREMENTS.md) | Problem analysis, requirements, constraints |
| [02-ARCHITECTURE.md](./02-ARCHITECTURE.md) | System design, components, data flow |
| [03-PHASE1-VRAM-TRACKING.md](./03-PHASE1-VRAM-TRACKING.md) | VRAM tracker implementation |
| [04-PHASE2-LIFECYCLE-MANAGER.md](./04-PHASE2-LIFECYCLE-MANAGER.md) | Service lifecycle management |
| [05-PHASE3-GPU-MANAGER-V2.md](./05-PHASE3-GPU-MANAGER-V2.md) | Core GPU manager integration |
| [06-PHASE4-WORKER-INTEGRATION.md](./06-PHASE4-WORKER-INTEGRATION.md) | Worker and API integration |
| [07-PHASE5-TESTING.md](./07-PHASE5-TESTING.md) | Testing strategy and test files |
| [08-VERIFICATION-CHECKLIST.md](./08-VERIFICATION-CHECKLIST.md) | Step-by-step verification guide |

## Quick Reference

### Pipeline Phases and GPU Services

```
Phase 1: Crawl       → No GPU needed      → release_all()
Phase 2: Analysis    → Vidi 7B (~4 GB)    → ensure_service("vidi")
Phase 3: Script+TTS  → CosyVoice (~4 GB)  → ensure_service("cosyvoice")
Phase 4: Video Gen   → ComfyUI (~20 GB)   → ensure_service("comfyui")
Phase 5: Render      → CPU only           → release_all()
```

### Service Priority (Higher = More Important)

| Service | Priority | VRAM | Type |
|---------|----------|------|------|
| ComfyUI | 100 | 20 GB | Native |
| CosyVoice | 50 | 4 GB | Docker |
| Vidi 7B | 40 | 4 GB | Native |
| Ollama | 10 | 18 GB | Docker |

### Files to Create/Modify

| File | Action | Phase |
|------|--------|-------|
| `middleware/requirements.txt` | Modify | 1 |
| `middleware/lib/vram_tracker.py` | Create | 1 |
| `middleware/lib/service_registry.py` | Create | 2 |
| `middleware/lib/lifecycle_manager.py` | Create | 2 |
| `middleware/lib/gpu_manager_v2.py` | Create | 3 |
| `middleware/worker.py` | Modify | 4 |
| `middleware/server.py` | Modify | 4 |
| `middleware/tests/test_gpu_manager_v2.py` | Create | 5 |

## Open Source Evaluation

| Solution | Verdict | Reason |
|----------|---------|--------|
| NVIDIA MPS | Not suitable | Shares VRAM, no isolation |
| NVIDIA MIG | Not available | Only A100/H100 |
| Kubernetes GPU | Overkill | Heavy infra for single machine |
| Ray | Not suitable | Requires Ray runtime for all tasks |
| Slurm | Overkill | HPC cluster scheduler |
| **Custom** | **Recommended** | Tailored, lightweight, fits stack |

## Success Criteria

- [ ] `/gpu/status` endpoint shows real-time VRAM usage
- [ ] Services auto-start when pipeline phase changes
- [ ] Lower-priority services preempted for higher-priority
- [ ] Health checks verify service ready before task dispatch
- [ ] Graceful shutdown reclaims VRAM within 5 seconds
- [ ] No OOM errors during normal pipeline operation
- [ ] 80%+ test coverage for new modules
