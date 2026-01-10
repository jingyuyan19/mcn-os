# MCN OS Documentation

**AI-Driven Video Production Pipeline**

> Complete documentation for AI agents and developers

---

## � Start Here (AI Agents)

| Document | Description |
|----------|-------------|
| [QUICKSTART.md](./QUICKSTART.md) | **New machine setup** - Prerequisites, install, secrets |
| [CURRENT_STATE.md](./CURRENT_STATE.md) | **What's done vs. next** - Component status, recent runs |
| [MASTER_ARCHITECTURE_BURGER.md](./MASTER_ARCHITECTURE_BURGER.md) | **Big picture** - System overview with diagrams |

---

## 📚 Full Documentation Index (23 Documents)

### 🏗️ Big Picture Architecture
| Document | Description |
|----------|-------------|
| [MASTER_ARCHITECTURE_BURGER.md](./MASTER_ARCHITECTURE_BURGER.md) | **System Overview** - "Burger Model" with Mermaid diagrams |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Quick reference architecture |
| [DEEPSEEK_BRAIN.md](./DEEPSEEK_BRAIN.md) | V8.0 Chain-of-Thought AI pipeline |
| [architecture_design.md](./architecture_design.md) | Original design philosophy |

### 🧠 The Brain (n8n + DeepSeek)
| Document | Description |
|----------|-------------|
| [N8N_WORKFLOWS.md](./N8N_WORKFLOWS.md) | Workflow guide, DeepSeek chain, HTTP nodes |
| [DEEPSEEK_BRAIN.md](./DEEPSEEK_BRAIN.md) | 4-stage pipeline: Analyst→Writer→Director→Editor |

### 💪 GPU Middleware
| Document | Description |
|----------|-------------|
| [MIDDLEWARE_API.md](./MIDDLEWARE_API.md) | API endpoints, task types, payloads |
| [ASYNC_MIDDLEWARE_DESIGN.md](./ASYNC_MIDDLEWARE_DESIGN.md) | Producer-Consumer architecture design |
| [GPU_INTEGRATION.md](./GPU_INTEGRATION.md) | ComfyUI, CosyVoice, VRAM management |

### 🎬 Video Rendering
| Document | Description |
|----------|-------------|
| [REMOTION_GUIDE.md](./REMOTION_GUIDE.md) | Timeline format, Composition.tsx, asset paths |
| [longcat_avatar_guide.md](./longcat_avatar_guide.md) | LongCat digital human LoRA |
| [FLUX2_RFC.md](./FLUX2_RFC.md) | Flux 2 investigation notes |

### 🎛️ Control Plane (Sanity CMS)
| Document | Description |
|----------|-------------|
| [SANITY_SCHEMAS.md](./SANITY_SCHEMAS.md) | All 8 schemas, GROQ queries, API access |

### 🛠️ DevOps & Operations
| Document | Description |
|----------|-------------|
| [GIT_STRATEGY.md](./GIT_STRATEGY.md) | Hybrid monorepo, LFS, backup scripts |
| [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) | Common issues and solutions |
| [PROJECT_STATUS.md](./PROJECT_STATUS.md) | Current feature status |

### 📋 Development History
| Document | Description |
|----------|-------------|
| [DEVELOPMENT_PLAN.md](./DEVELOPMENT_PLAN.md) | Full development roadmap |
| [PHASE7_INTEGRATION.md](./PHASE7_INTEGRATION.md) | n8n→Middleware integration |
| [PHASE8_REMOTION.md](./PHASE8_REMOTION.md) | Remotion engine implementation |
| [PHASE9_MVP.md](./PHASE9_MVP.md) | DeepSeek Brain MVP scope |

---

## 🚀 Quick Start

```bash
# 1. Start infrastructure
docker compose up -d

# 2. Start GPU services
./start_comfy.sh &
./start_middleware.sh

# 3. Access n8n
open http://localhost:5678

# 4. Run brain workflow
# Import: n8n/workflows/3_Orchestrator_V8_8.json
```

---

## 🔑 Key Endpoints

| Service | URL |
|---------|-----|
| n8n | http://localhost:5678 |
| Sanity Studio | http://localhost:3333 |
| Middleware API | http://localhost:8000 |
| Asset Server | http://localhost:8081 |
| ComfyUI | http://localhost:8188 |

---

## 📂 Project Structure

```
mcn/
├── docs/              # 📚 Documentation (21 files)
├── n8n/workflows/     # 🧠 n8n automation
├── middleware/        # 💪 GPU task processing
├── rendering/         # 🎬 Remotion composition
├── sanity-studio/     # 🎛️ CMS schemas
├── assets/            # 📁 Media & output
├── models/            # 🤖 AI model weights
└── config/            # ⚙️ Service configs
```

---

## 🤖 For AI Agents

When working on this system:

1. **Start Here**: `MASTER_ARCHITECTURE_BURGER.md` → Big picture
2. **Brain Logic**: `DEEPSEEK_BRAIN.md` + `N8N_WORKFLOWS.md`
3. **GPU Tasks**: `MIDDLEWARE_API.md` + `GPU_INTEGRATION.md`
4. **Video Output**: `REMOTION_GUIDE.md`
5. **Data Models**: `SANITY_SCHEMAS.md`
6. **Issues**: `TROUBLESHOOTING.md`

---

## 📊 Documentation Stats

| Category | Files | Size |
|----------|-------|------|
| Architecture | 4 | ~16KB |
| Components | 7 | ~28KB |
| Operations | 3 | ~11KB |
| History | 4 | ~14KB |
| **Total** | **21** | **~69KB** |

---

*Last Updated: 2026-01-07*
