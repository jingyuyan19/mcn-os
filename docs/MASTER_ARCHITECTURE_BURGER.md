# 🏗️ Digital MCN OS - Master Architecture

**Version**: 1.1 (Phase 10: Production Hardening)  
**Last Updated**: 2026-01-07  
**Status**: Live / Production Ready  
**Repository**: `https://github.com/jingyuyan19/mcn-os.git`

---

## 1. 🧩 System Overview: The "Burger Model"

The system is a "Virtual Artist ERP" designed to automate video production using a Control Plane (Sanity), an AI Brain (n8n + DeepSeek), and a GPU Factory (ComfyUI/CosyVoice/Remotion).

```mermaid
graph TD
    User((User)) -->|Manage| A[Sanity CMS (Control Plane)]
    A -->|Webhook| B[n8n + DeepSeek (Brain)]
    
    subgraph "Infrastructure (Hybrid Monorepo)"
        B -->|HTTP Task| C[Python Middleware]
        C -->|Queue| D[Redis]
        E[GPU Worker] -->|Poll| D
        E -->|Exec| F[ComfyUI / CosyVoice]
        G[Remotion Engine] -->|Render| H[Final MP4]
        n8n -->|CLI| G
    end
    
    F -->|Assets| G
    E -->|Update Status| D
    E -->|Callback| B
    B -->|Update Status| A
```

---

## 2. 📂 Project Structure (Hybrid Monorepo)

**Philosophy**: Code in Git, Logic in JSON, Assets in LFS, Models in Symlinks.

```text
/mcn/
├── sanity-studio/       # Control Plane (TypeScript)
├── n8n/                 # Orchestration (Workflow JSONs)
│   ├── workflows/       # 1_Schedule, 2_Post, 3_Renderer, Orchestrator
├── middleware/          # GPU Factory Integration (Python)
│   ├── server.py        # FastAPI Producer
│   ├── worker.py        # Background Consumer
│   └── lib/             # ComfyDriver, RedisClient
├── rendering/           # Remotion Render Engine
├── docker/              # Dockerfiles (CosyVoice, etc.)
├── scripts/             # DevOps (Backup, Setup)
└── assets/              # Shared Volume (Generated Media)
```

---

## 3. 🧠 Component Details

### 3.1 Control Plane (Sanity CMS) ✅
*   **Role**: ERP for Artists, Schedules, and Production Orders.
*   **Key Schemas**: `artist`, `schedule`, `post`, `voice`, `wardrobe`, `studio`, `source`, `prompt_config`
*   **Unique Features**:
    *   GROQ Filters for wardrobe validation.
    *   "Locked" shots (preserves human edits during AI regeneration).

### 3.2 Brain (n8n + DeepSeek V3) ✅
*   **Role**: Chain-of-Thought AI Pipeline.
*   **Stages**:
    1. **Analyst**: Extract key facts → Intelligence JSON
    2. **Writer**: Apply persona → Script Array
    3. **Director**: Plan visuals → Visual Prompts
    4. **Editor**: Calculate timings → Timeline JSON
*   **Workflow**: `3_Orchestrator_V8_8.json`

### 3.3 GPU Factory (Middleware V8.5) ✅
*   **Role**: Async Task Processing for Hardware.
*   **Architecture**:
    *   **API**: FastAPI (`server.py`) - Lightweight, non-blocking.
    *   **Queue**: Redis (List: `task_queue`, Hash: `tasks:{id}`).
    *   **Worker**: `worker.py` - Single-threaded consumer.
*   **Features**:
    *   **Template Injection**: Replaces `{{KEY}}` in ComfyUI JSONs.
    *   **VRAM Management**: Aggressive garbage collection.
    *   **GPU Lock**: Prevents VRAM collision.

### 3.4 Voice Engine (CosyVoice v3) ✅ **NEW**
*   **Role**: Zero-shot voice cloning TTS.
*   **Docker Image**: `cosyvoice:v3-vpn` (Golden Environment)
*   **API**: `POST /inference_zero_shot` (multipart/form-data)
*   **Languages**: English + Chinese verified working
*   **Status**: Trembling audio issue **RESOLVED** (2026-01-07)

### 3.5 Render Engine (Remotion) ✅
*   **Role**: JSON-to-MP4 video composition.
*   **File**: `rendering/src/Composition.tsx`
*   **Driver**: `middleware/lib/remotion_driver.py`

---

## 4. 🚀 Deployment & DevOps

### 4.1 Service Endpoints
| Service | URL | Status |
|---------|-----|--------|
| n8n | http://localhost:5678 | ✅ Docker |
| Sanity Studio | http://localhost:3333 | ✅ Local |
| Middleware API | http://localhost:8000 | ✅ Host |
| CosyVoice | http://localhost:50000 | ✅ Docker |
| Asset Server | http://localhost:8081 | ✅ Docker |
| ComfyUI | http://localhost:8188 | ✅ Host |

### 4.2 Disaster Recovery
*   **Scripts**:
    *   `backup_n8n.sh`: Exports workflows and credentials.
    *   `setup_models.sh`: Symlinks large models from `~/.cache`.
*   **Git Strategy**:
    *   `models/` ignored.
    *   `.gitattributes` tracks `*.mp4`, `*.png` (LFS).
*   **Docker data-root**: `/mnt/data_ssd/docker-data` (SSD)

---

## 5. ✅ Completed Phases

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Infrastructure & Atomic Units | ✅ Complete |
| 2 | Complex Chains (LongCat) | ✅ Complete |
| 3 | Middleware Layer | ✅ Complete |
| 4-5 | n8n Automation & DevOps | ✅ Complete |
| 6-7 | GPU Integration & E2E Test | ✅ Complete |
| 8 | Remotion Engine | ✅ Complete |
| 9 | DeepSeek Brain MVP | ✅ Complete |
| 10 | CosyVoice Golden Environment | ✅ Complete |

---

## 6. 🔮 Future Roadmap

*   **Commercial**: Social media API integration (TikTok, YouTube)
*   **Distribution**: CDN asset serving, multi-region deployment
*   **Scaling**: GPU cluster support, queue prioritization
