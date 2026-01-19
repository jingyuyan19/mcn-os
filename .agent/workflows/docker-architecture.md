---
description: Docker container management for MCN OS
---

# Docker Architecture

MCN OS uses a Docker-first architecture with 16+ containers.

## Container Overview

| Container | Port | Description |
|-----------|------|-------------|
| mcn_core | 8000 | Middleware + BettaFish ("The Citadel") |
| mcn_signsrv | 8989 | XHS/Douyin signature generation |
| mcn_mediacrawler | 8001 | Playwright crawler for social media |
| mcn_comfyui | 8188 | Image generation (profile: art) |
| mcn_ollama | 11434 | Local LLM (DeepSeek/Qwen) |
| mcn_cosyvoice | 50000 | AI Voice synthesis |
| mcn_n8n | 5678 | Workflow orchestration |
| mcn_dozzle | 8888 | Unified log viewer |
| mcn_redis | 6379 | Cache + GPU lock |
| mcn_mysql | 3306 | MediaCrawlerPro data |
| mcn_postgres | 5432 | n8n data |

## Common Commands

### Start All Services
// turbo
```bash
cd /home/jimmy/Documents/mcn && docker-compose up -d
```

### Start ComfyUI (GPU)
// turbo
```bash
cd /home/jimmy/Documents/mcn && docker-compose --profile art up -d comfyui
```

### View Logs
// turbo
```bash
docker-compose logs -f mcn-core
```

### Rebuild a Container
```bash
docker-compose build --no-cache mcn-core
docker-compose up -d mcn-core
```

### Stop All
```bash
docker-compose down
```

## Key Files

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Main service definitions |
| `docker/mcn-core.Dockerfile` | Middleware + BettaFish container |
| `docker/requirements-core.txt` | Python dependencies (CPU torch) |

## Environment Variables

### mcn-core
- `REDIS_URL=redis://:123456@redis:6379/0`
- `MYSQL_HOST=mysql`
- `PYTHONPATH=/app/external/BettaFish:/app/middleware:/app/external/Vidi`

### mediacrawler
- `RELATION_DB_HOST=mysql`
- `REDIS_DB_HOST=redis`
- `SIGN_SRV_HOST=signsrv`

### ollama
- `OLLAMA_KEEP_ALIVE=5m` (auto-unload after 5 min idle)

## GPU Sharing (Anchored Tenant)

```
CosyVoice (anchor): ~4GB VRAM - Always running
Ollama (tenant):    ~18GB - Evictable via API
ComfyUI (tenant):   ~16GB - On-demand via profile
```

Use `GPUManager` for lock-based VRAM sharing:
```python
from lib.gpu_manager import get_gpu_manager
gpu = get_gpu_manager()
with gpu.acquire_gpu("comfyui", evict_ollama=True):
    # GPU-exclusive task
    pass
```
