# MCN OS - AI Video Content Generation System

Cognitive Operating System for AI-generated video content. Orchestrates AI artists that discover trends, research topics, generate scripts, and produce videos.

## Architecture Reference

See [@docs/MASTER_ARCHITECTURE_BURGER.md](docs/MASTER_ARCHITECTURE_BURGER.md) for full system design.

**3-Layer Model**: Perception (Scout) → Cognition (Brain) → Action (Factory)

## Quick Start Commands

```bash
# Start entire system
cd /home/jimmy/Documents/mcn && ./start_mcn_os.sh

# Check service health
docker ps | grep mcn_

# View logs
docker logs mcn_core --tail 100 --follow

# Run tests
docker exec mcn_core pytest middleware/tests/ -v

# Access API docs
curl http://localhost:8000/docs
```

## Service Endpoints

- **Middleware API**: http://localhost:8000 (FastAPI)
- **Sanity Studio**: http://localhost:3333 (CMS)
- **n8n**: http://localhost:5678 (Workflows)
- **ComfyUI**: http://localhost:8188 (Image/video)
- **CosyVoice**: http://localhost:50000 (TTS)

## Worker Management

The **Redis Worker** processes async tasks (media analysis, etc.) and is **automatically started** by `start_mcn_os.sh`.

```bash
# Check worker status
./scripts/check_worker.sh

# Check status with logs
./scripts/check_worker.sh --status

# Restart worker if needed
./scripts/check_worker.sh --restart

# View live worker logs
tail -f middleware/worker.log
```

**Troubleshooting:**
- Worker PID: `worker.pid`
- Worker logs: `middleware/worker.log`
- If async tasks remain "queued", the worker may not be running
- Worker auto-starts on system startup via `start_mcn_os.sh`

## Code Style

### Python
- Use `logger.info()` not `print()` for production code
- Async functions for I/O operations (Sanity, external APIs)
- Type hints required for all function signatures
- Import order: stdlib → third-party → local (`middleware.lib.*`)

### Error Handling
```python
# ✅ Correct: Specific error with context
try:
    result = await api_call()
except APIError as e:
    logger.error(f"API failed: {e}", exc_info=True)
    raise

# ❌ Wrong: Bare except or silent failure
try:
    result = api_call()
except:
    pass
```

## Testing Requirements

```bash
# Test individual module
docker exec mcn_core pytest middleware/tests/test_flow1_orchestrator.py -v

# Test with markers
docker exec mcn_core pytest -m "not slow" middleware/tests/

# Coverage report
docker exec mcn_core pytest --cov=middleware/lib middleware/tests/
```

**Coverage target**: 80%+ for new code

## Critical Patterns

### 1. Sanity Client Usage

**IMPORTANT**: Always use the singleton client with proper SSL configuration.

```python
from middleware.lib.sanity_client import get_sanity_client

client = get_sanity_client()  # Thread-safe singleton
artist = client.query('*[_id == $id][0]', {"id": artist_id})
```

**DO NOT** use Sanity MCP tools - Python client has robust SSL and retry logic.

### 2. Planning Session (策划会) is Mandatory

**All topics MUST go through planning session before script generation**:

```
candidate → analyzing → ir_ready → [PLANNING SESSION] → brief_ready → scripted
```

Skipping this step produces off-brand content.

### 3. Ollama Fallback Pattern

All agents support Antigravity → Ollama fallback:
```python
try:
    response = antigravity_client.chat(...)
except Exception:
    # Automatic fallback to Ollama
    response = ollama_fallback(...)
```

### 4. Topic Selection: Multi-Factor + Clustering

```python
score = (
    recency * weight.recency +
    relevance * weight.relevance +
    source_priority * weight.source +
    novelty * weight.novelty
)
# Then cluster by semantic similarity, pick top 3
```

## Environment Variables

**Required in `middleware/.env`**:
```bash
SANITY_PROJECT_ID=4t6f8tmh
SANITY_API_TOKEN=sk-...
MYSQL_HOST=mysql
DB_PASSWORD=123456
REDIS_URL=redis://:123456@redis:6379/0
```

**Flow 1 Testing**:
```bash
FLOW1_TEST_MODE=true  # Bypass schedule checks
```

## Common Workflows

### Test Flow 1 End-to-End
```bash
# Get testable artist
curl -s http://localhost:8000/flow1/test-artists | jq -r '.artists[0]._id'

# Trigger (skip crawl for speed)
curl -X POST "http://localhost:8000/flow1/test-trigger/$ARTIST_ID?skip_crawl=true"

# Get diverse candidates
curl -s "http://localhost:8000/flow1/candidates-clustered/$NICHE_ID" | jq

# Run analysis with planning
curl -X POST "http://localhost:8000/flow1/run-analysis/$TOPIC_ID"
```

### Debug MediaCrawler Issues
```bash
# Check crawler health
curl -s http://localhost:8000/mediacrawler/check-cookies | jq

# View recent logs
docker logs mcn_mediacrawler --tail 100 | grep -i "验证码\|captcha"

# Reset account status
docker exec mcn_mysql mysql -uroot -p123456 media_crawler_pro \
  -e "UPDATE crawler_cookies_account SET status = 0 WHERE platform_name = 'xhs';"
```

### Debugging BettaFish Analysis
```bash
# Check analysis status
curl -s "http://localhost:8000/flow1/analysis-status/$TOPIC_ID" | jq

# View analysis logs
docker logs mcn_core --tail 200 | grep -i "bettafish\|forumengine"
```

## Hot-Reload Behavior

- ✅ **Auto-reload**: `middleware/*.py`, `external/BettaFish/**`
- ❌ **Requires restart**: `requirements.txt`, environment variables, Docker config

```bash
# After changing dependencies
docker restart mcn_core
```

## GPU Management

### GPU Manager V2 (CRITICAL)

The system uses **GPU Manager V2** (`middleware/lib/gpu_manager_v2.py`) to prevent OOM errors on the 24GB RTX 4090 by orchestrating GPU services based on pipeline phase.

**Service Priority** (higher = won't be preempted):
| Service | Priority | VRAM | Pipeline Phase |
|---------|----------|------|----------------|
| ComfyUI | 100 | 20 GB | 4 (Video Gen) |
| CosyVoice | 50 | 4 GB | 3 (TTS) |
| Vidi 7B | 40 | 4 GB | 2 (Analysis) |
| Ollama | 10 | 18 GB | - (Fallback) |

**Pipeline Phase Mapping**:
```
Phase 1: Crawl       → No GPU        → release_all()
Phase 2: Analysis    → Vidi (4 GB)   → ensure_service("vidi")
Phase 3: TTS         → CosyVoice (4 GB)
Phase 4: Video Gen   → ComfyUI (20 GB)
Phase 5: Render      → No GPU
```

**GPU API Endpoints**:
```bash
# Check GPU status (VRAM, services, lock)
curl http://localhost:8000/gpu/status

# Prepare for pipeline phase (auto starts/stops services)
curl -X POST http://localhost:8000/gpu/prepare-phase/4

# Manual service control
curl -X POST http://localhost:8000/gpu/service/comfyui/start
curl -X POST http://localhost:8000/gpu/service/cosyvoice/stop

# Release all GPU services
curl -X POST http://localhost:8000/gpu/release-all

# Force release GPU lock (use with caution)
curl -X POST http://localhost:8000/gpu/lock/release
```

**Key Modules**:
- `lib/vram_tracker.py` - Real-time VRAM monitoring via pynvml
- `lib/service_registry.py` - Service configs (VRAM, priority, phases)
- `lib/lifecycle_manager.py` - Start/stop Docker & native services
- `lib/gpu_manager_v2.py` - Unified orchestration with Redis locking

**Usage in Worker**:
```python
from lib.gpu_manager_v2 import get_gpu_manager_v2

# Context manager handles locking and service lifecycle
async with gpu_manager.use_service("comfyui") as ready:
    if ready:
        result = comfy_driver.execute_workflow(...)
```

### Legacy GPU Config

- **ComfyUI**: Runs natively via `start_comfy.sh` (best GPU access)
- **CosyVoice, Ollama**: Run in Docker with GPU passthrough
- Use `--smart-memory --cpu-vae` flags for VRAM optimization

### ComfyUI Configuration (CRITICAL)

ComfyUI runs **natively on the host**, not in Docker. The Docker container `mcn_core` must reach it via the Docker network gateway.

**Required in `middleware/.env`**:
```bash
# ComfyUI runs on host, Docker containers reach it via gateway
COMFY_HOST=172.18.0.1
COMFY_PORT=8188
```

**How to find the correct gateway IP**:
```bash
docker inspect mcn_core --format '{{range .NetworkSettings.Networks}}{{.Gateway}}{{end}}'
```

**Verify connectivity**:
```bash
# From host
curl -s "http://localhost:8188/system_stats" | jq '.system.python_version'

# From Docker container
docker exec mcn_core curl -s "http://172.18.0.1:8188/system_stats"
```

**If ComfyUI is not running**:
```bash
cd /home/jimmy/Documents/mcn && ./start_comfy.sh
# Or manually:
cd /mnt/data_ssd/mcn/visual/ComfyUI && source venv/bin/activate && python main.py --listen 0.0.0.0 --port 8188
```

## Startup Procedure (CRITICAL)

**ALWAYS use the official startup script**:
```bash
cd /home/jimmy/Documents/mcn && ./start_mcn_os.sh
```

This script:
1. Starts Docker services via docker-compose
2. Starts the Redis Worker (native, uses middleware/.venv)
3. Opens Sanity Studio in a terminal
4. Starts ngrok for webhooks
5. Starts Vidi 7B (native GPU)
6. Starts ComfyUI (native GPU)

**DO NOT** start services manually unless debugging.

### Service Architecture

| Service | Runs In | Port | Notes |
|---------|---------|------|-------|
| mcn_core (Middleware) | Docker | 8000 | FastAPI server |
| Redis Worker | Native (.venv) | - | Processes async tasks |
| ComfyUI | Native | 8188 | GPU video generation |
| Vidi 7B | Native | 8099 | Video understanding |
| Sanity Studio | Native (npm) | 3333 | CMS dev server |
| mcn_mediacrawler | Docker | 8010 | Social media crawler |
| mcn_cosyvoice | Docker | 50000 | TTS with GPU |

### Common Port Conflicts

If startup fails with "port already allocated":
```bash
# Find orphan containers
docker ps -a | grep -E "surrealdb|homepage|sanity_studio|open_notebook"

# Remove them
docker rm -f mcn_surrealdb mcn_homepage mcn_sanity_studio mcn_open_notebook 2>/dev/null

# Restart
./start_mcn_os.sh
```

## Platform Codes (MediaCrawlerPro)

**Use correct codes**:
- `xiaohongshu` (NOT xhs)
- `douyin` (NOT dy)
- `bilibili` (NOT bili)

Wrong codes return HTTP 422.

## File References

Key implementation files:
- **Flow 1**: `middleware/lib/flow1_orchestrator.py`
- **Planning Session**: `middleware/lib/planning_session.py`
- **Sanity Client**: `middleware/lib/sanity_client.py`
- **BettaFish**: `external/BettaFish/`
- **Schemas**: `sanity-studio/schemaTypes/`

Detailed docs in `docs/` directory.

## Troubleshooting

### "No schedules returned"
- Check artist has `primaryFlowType: "social"`
- Check `nicheConfig` reference exists
- Check `crawlSchedule` configured
- Use `?test_mode=true` to bypass schedule

### Analysis Takes Too Long
- Check BettaFish logs: `docker logs mcn_core --tail 100`
- Expected time: 10-30 minutes depending on depth
- Use `depth=quick` for faster testing

### CAPTCHA Detection
- Cookie validator checks: validity + freshness + volume
- Valid cookies + no data = CAPTCHA block
- Reset via Cookie Health Monitor

## Documentation

- **Current State**: `docs/CURRENT_STATE.md`
- **Architecture**: `docs/MASTER_ARCHITECTURE_BURGER.md`
- **Perception Layer**: `docs/PERCEPTION_ARCHITECTURE.md`
- **Flow 1 Guide**: `docs/FLOW1_TEST_GUIDE.md`
- **API Reference**: `.agent/workflows/flow-1-social-crawler.md`
