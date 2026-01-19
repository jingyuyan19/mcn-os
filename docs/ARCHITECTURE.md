# MCN OS - Architecture Overview

## Introduction

MCN OS is an **AI Artist Operating System** - a headless, event-driven Digital MCN (Multi-Channel Network) that manages AI-generated content creation and distribution.

## Architecture (Docker-First)

As of January 2026, MCN OS runs on a **Docker-first architecture** with 16+ containers:

```
┌─────────────────────────────────────────────────────────────────┐
│                         MCN OS                                   │
├─────────────────────────────────────────────────────────────────┤
│  Control Layer                                                   │
│  ├── Sanity Studio (Native) → Content Management                │
│  └── n8n (Docker) → Workflow Orchestration                      │
├─────────────────────────────────────────────────────────────────┤
│  Brain Layer (Docker)                                            │
│  ├── mcn-core → Middleware API + BettaFish Engines              │
│  ├── Ollama → Local LLM (DeepSeek/Qwen)                         │
│  └── Whisper → Speech-to-Text                                   │
├─────────────────────────────────────────────────────────────────┤
│  Perception Layer (Docker)                                       │
│  ├── mediacrawler → Social Media Scraping                       │
│  ├── signsrv → XHS/Douyin Signature Generation                  │
│  └── RSSHub → Universal Feed Converter                          │
├─────────────────────────────────────────────────────────────────┤
│  Visual Layer (Docker, profile: art)                             │
│  └── ComfyUI → Image/Video Generation                           │
├─────────────────────────────────────────────────────────────────┤
│  Audio Layer (Docker)                                            │
│  └── CosyVoice → AI Voice Synthesis                             │
├─────────────────────────────────────────────────────────────────┤
│  Data Layer (Docker)                                             │
│  ├── PostgreSQL → n8n Data                                      │
│  ├── MySQL → MediaCrawlerPro Data                               │
│  ├── Redis → Cache + GPU Lock                                   │
│  └── Qdrant → Vector Memory                                     │
└─────────────────────────────────────────────────────────────────┘
```

## Key Components

### mcn-core (The Citadel)
- **FastAPI Middleware** + **BettaFish Engines** in one container
- Handles all API requests, research workflows, content generation
- Connected via `PYTHONPATH` for in-process imports

### BettaFish Engines
- **InsightEngine** - Deep topic analysis
- **MediaEngine** - Social media content processing
- **QueryEngine** - Intelligent search
- **ForumEngine** - Multi-agent orchestration
- **ReportEngine** - Document generation

### GPU Sharing (Anchored Tenant)
- **CosyVoice** (anchor): ~4GB VRAM, always running
- **Ollama** (tenant): ~18GB, evictable via API
- **ComfyUI** (tenant): ~16GB, on-demand via profile
- **GPUManager** class manages Redis lock for VRAM

## Quick Start

```bash
# Start all services
./start_mcn_os.sh

# Start ComfyUI when needed
docker-compose --profile art up -d comfyui

# View logs
open http://localhost:8888  # Dozzle
```

## Service URLs

| Service | URL |
|---------|-----|
| Middleware | http://localhost:8000 |
| Sanity Studio | http://localhost:3333 |
| n8n | http://localhost:5678 |
| ComfyUI | http://localhost:8188 |
| Dozzle (Logs) | http://localhost:8888 |

## Key Files

| File | Purpose |
|------|---------|
| `docker-compose.yml` | All Docker service definitions |
| `docker/mcn-core.Dockerfile` | Middleware + BettaFish container |
| `middleware/lib/gpu_manager.py` | GPU lock with Redis |
| `start_mcn_os.sh` | Master startup script |
