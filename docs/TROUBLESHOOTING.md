# Troubleshooting Guide

Quick reference for common issues across all subsystems.

---

## n8n Issues

| Symptom | Cause | Solution |
|---------|-------|----------|
| `Cannot read 'nodeName'` | Using deprecated `Start` node | Use `Manual Trigger` node instead |
| Empty query parameters | Wrong JSON format | Use `queryParameters.parameters[]` |
| Expression not resolved | Missing wrapper | Use `={{ expression }}` |
| Can't reach middleware | Wrong host in Docker | Use `172.17.0.1:8000` |
| Workflow won't save | Invalid JSON in Code node | Check syntax errors |

---

## Middleware Issues

| Symptom | Cause | Solution |
|---------|-------|----------|
| "Connection refused :8000" | Server not running | `python server.py` |
| "Connection refused :6379" | Redis not running | `docker compose up redis -d` |
| Task stuck in queue | Worker not running | `python worker.py` |
| "Template not found" | Missing workflow file | Check `middleware/workflows/` |

---

## Remotion Issues

| Symptom | Cause | Solution |
|---------|-------|----------|
| "net::ERR_BLOCKED_BY_ORB" | Asset URL doubled | Use relative paths only |
| "delayRender timeout" | Video file 404 | Check asset server + file exists |
| "Bundler version mismatch" | npm packages out of sync | `npm install` in rendering/ |
| Black frames | Codec issue | Use h264 with yuv420p |
| High memory usage | Too many concurrent frames | Set `concurrency: 1` |

---

## ComfyUI Issues

| Symptom | Cause | Solution |
|---------|-------|----------|
| "CUDA out of memory" | Not enough VRAM | Close apps, restart ComfyUI |
| "Model not found" | Wrong path | Check ComfyUI model settings |
| WebSocket timeout | Long generation | Increase client timeout |
| "Workflow invalid" | Missing node | Install required custom nodes |

---

## Sanity Issues

| Symptom | Cause | Solution |
|---------|-------|----------|
| "Unknown query parameter" | Wrong query format | URL-encode the query |
| "Unauthorized" | Missing/wrong token | Check API token in n8n |
| Schema not appearing | Not registered | Add to `schemaTypes/index.ts` |
| CORS error | Studio misconfigured | Check `sanity.config.ts` |

---

## Docker Issues

| Symptom | Cause | Solution |
|---------|-------|----------|
| Container not starting | Port conflict | Check `docker ps`, kill conflicts |
| Volume not mounted | Path doesn't exist | Create directory first |
| Network unreachable | Wrong network name | Use `mcn_network` |
| Database connection failed | Postgres not ready | Wait 5 seconds, retry |

---

## General Debugging

### Check Logs
```bash
# Middleware
tail -f middleware/worker.log

# n8n
docker logs mcn_n8n -f

# Redis
docker logs mcn_redis -f
```

### Test Endpoints
```bash
# Middleware API
curl http://localhost:8000/health

# Asset Server
curl -I http://localhost:8081/assets/videos/test.mp4

# Sanity
curl "https://4t6f8tmh.api.sanity.io/v2024-01-01/data/query/production?query=*[_type==\"artist\"]"
```

### Restart Services
```bash
# All Docker services
docker compose restart

# Middleware only
pkill -f "python worker.py"
./start_middleware.sh

# ComfyUI
pkill -f "python main.py"
./start_comfy.sh
```

---

## Quick Health Check

```bash
# 1. Docker services
docker compose ps

# 2. Middleware
curl localhost:8000/health

# 3. Redis
docker exec mcn_redis redis-cli ping

# 4. n8n
curl -I localhost:5678

# 5. Asset server
curl -I localhost:8081/assets/
```
