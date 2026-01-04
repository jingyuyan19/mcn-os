# 🏗️ Digital MCN OS - Master Architecture

**Version**: 1.0 (Post-Phase 7)
**Status**: Live / In Development
**Repository**: `https://github.com/jingyuyan19/mcn-os.git`

---

## 1. 🧩 System Overview: The "Burger Model"

The system is a "Virtual Artist ERP" designed to automate video production using a Control Plane (Sanity), an Orchestrator (n8n), and a GPU Factory (ComfyUI/Middleware).

```mermaid
graph TD
    User((User)) -->|Manage| A[Sanity CMS (Control Plane)]
    A -->|Webhook| B[n8n (Orchestrator)]
    
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
│   ├── workflows/       # 1_Schedule, 2_Post, 3_Renderer
├── middleware/          # GPU Factory Integration (Python)
│   ├── server.py        # FastAPI Producer
│   ├── worker.py        # Background Consumer
│   └── lib/             # ComfyDriver, RedisClient
├── remotion-project/    # [Phase 8] Intelligent Render Engine
├── scripts/             # DevOps (Backup, Setup)
└── assets/              # Shared Volume (Generated Media)
```

---

## 3. 🧠 Component Details

### 3.1 Control Plane (Sanity CMS)
*   **Role**: ERP for Artists, Schedules, and Production Orders.
*   **Key Schemas**:
    *   `artist.ts`: Defines character DNA and visual masters.
    *   `schedule.ts`: Visual timeline for automated trigger rules.
    *   `post.ts`: The "Storyboard" - contains shot-by-shot data for the video.
*   **Unique Features**:
    *   GROQ Filters for wardrobe validation.
    *   "Locked" shots (preserves human edits during AI regeneration).

### 3.2 Orchestrator (n8n)
*   **Role**: Logic Glue. Connects Sanity, DeepSeek, and GPU.
*   **Workflows**:
    *   `1_Schedule_Poller`: Runs cron -> Creates `Draft` Posts.
    *   `2_Post_Generator`: Calls DeepSeek -> Writes Storyboard to Sanity.
    *   `3_Video_Renderer`: Polls Middleware -> Updates Sanity Status.

### 3.3 GPU Factory (Middleware V8.0)
*   **Role**: Async Task Processing for Hardware.
*   **Architecture**:
    *   **API**: FastAPI (`server.py`) - Lightweight, non-blocking.
    *   **Queue**: Redis (List: `task_queue`, Hash: `tasks:{id}`).
    *   **Worker**: `worker.py` - Single-threaded consumer (prevents GPU VRAM collision).
*   **Features**:
    *   **Template Injection**: Replaces `{{KEY}}` in ComfyUI JSONs.
    *   **VRAM Management**: Aggressive garbage collection between tasks.
    *   **Smart Polling**: n8n polls status, avoiding HTTP timeout issues.

---

## 4. 🚀 Deployment & DevOps

### 4.1 Networking
*   **n8n (Docker)** -> **Host**: `http://172.17.0.1:8000`
*   **Sanity Cloud** -> **n8n**: Requires Public URL (or manual trigger for dev).
*   **Remotion** -> **Assets**: `http://localhost:8081/assets/` (via Nginx).

### 4.2 Disaster Recovery
*   **Scripts**:
    *   `backup_n8n.sh`: Exports workflows and credentials.
    *   `setup_models.sh`: Symlinks large models from `~/.cache` to avoid Git bloat.
*   **Git Strategy**:
    *   `models/` ignored.
    *   `.gitattributes` tracks `*.mp4`, `*.png` (LFS).

---

## 5. 🔮 Future Roadmap (Phase 8+)
*   **Remotion Engine**: CPU-based video assembler (React).
*   **DeepSeek Director**: LLM outputting accurate Timeline JSONs.
*   **Nginx Asset Server**: Serving local assets to the headless renderer.
