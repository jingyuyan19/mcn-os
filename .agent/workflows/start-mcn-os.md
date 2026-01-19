---
description: Start all MCN OS services (Docker-first architecture)
---

# Start MCN OS (Docker-First)

Run this workflow to start all MCN OS services after a system reboot.

## Quick Start
// turbo
1. Run the master startup script:
```bash
cd /home/jimmy/Documents/mcn && ./start_mcn_os.sh
```

## What It Starts

| Service | URL | Type |
|---------|-----|------|
| mcn-core (Middleware) | http://localhost:8000 | Docker |
| SignSrv | http://localhost:8989 | Docker |
| MediaCrawler | http://localhost:8001 | Docker |
| n8n | http://localhost:5678 | Docker |
| Ollama | http://localhost:11434 | Docker |
| Dozzle (Logs) | http://localhost:8888 | Docker |
| Sanity Studio | http://localhost:3333 | Native |

## ComfyUI (On-Demand GPU)

ComfyUI uses Docker profiles and is NOT started by default to save GPU VRAM:

// turbo
2. Start ComfyUI when needed:
```bash
cd /home/jimmy/Documents/mcn && docker-compose --profile art up -d comfyui
```

After starting, access at: http://localhost:8188

## View Logs

### Dozzle (Web UI)
Open http://localhost:8888 in browser for unified log viewing.

### CLI
```bash
docker-compose logs -f mcn-core
docker-compose logs -f mediacrawler
```

## Individual Service Commands

### All Docker Services
```bash
cd /home/jimmy/Documents/mcn
docker-compose up -d
```

### Sanity Studio (Native)
```bash
cd /home/jimmy/Documents/mcn/sanity-studio
npm run dev
```

### Restart mcn-core
```bash
docker-compose restart mcn-core
```

## GPU Manager

The system includes a Redis-based GPU lock for managing VRAM:

```python
from lib.gpu_manager import get_gpu_manager
gpu = get_gpu_manager()

# Check GPU status
status = gpu.get_gpu_status()

# Acquire GPU with optional Ollama eviction
with gpu.acquire_gpu("comfyui", evict_ollama=True):
    # Run GPU-intensive task
    pass
```

## Troubleshooting

### Port Already in Use
```bash
# Find process using port
lsof -i :8000
# Kill the process
kill -9 <PID>
```

### Container Not Starting
```bash
# Check logs
docker logs mcn_core
# Rebuild container
docker-compose build mcn-core
docker-compose up -d mcn-core
```

### Redis Authentication Error
Ensure REDIS_URL includes password:
```
redis://:123456@redis:6379/0
```
