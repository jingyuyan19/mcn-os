# Digital MCN OS - Git Version Control Strategy

**Goal**: A sustainable version control system for a project mixing Production Code (TS/Python), Low-Code (n8n/ComfyUI), Docker Containers, and Huge Assets (Models/Video).

**Core Philosophy**: "Code in Git, Logic in JSON, Models in Scripts, Assets in LFS, Infrastructure as Code."

---

## 1. 📂 Directory Structure (Docker-First Architecture)

Git Root: `/home/jimmy/Documents/mcn`

```text
/home/jimmy/Documents/mcn/  (Git Root)
├── .git/
├── .gitignore               # 🛡️ Ignores 10GB+ folders
├── .gitattributes           # 📦 LFS: Handles binary assets
├── docker-compose.yml       # ⚙️ Main container definitions
├── start_mcn_os.sh          # 🚀 Master startup script
├── README.md

├── docker/                  # [NEW] Docker Build Files
│   ├── mcn-core.Dockerfile  # ✅ TRACK: Middleware container
│   └── requirements-core.txt # ✅ TRACK: Python dependencies

├── middleware/              # [Code] Python API (Runs in mcn-core container)
│   ├── lib/                 # Core libraries (gpu_manager.py, etc.)
│   ├── server.py            # FastAPI entry point
│   └── requirements.txt     # Native dev dependencies

├── external/                # [External Projects] Bind-mounted into containers
│   ├── BettaFish/           # ❌ IGNORE: Submodule or separate repo
│   ├── MediaCrawlerPro-Python/      # ❌ IGNORE: Has own Dockerfile
│   └── MediaCrawlerPro-SignSrv/     # ❌ IGNORE: Has own Dockerfile

├── sanity-studio/           # [Code] CMS Control Plane (Native)
│   ├── schemaTypes/
│   └── sanity.config.ts

├── rendering/               # [Code] Remotion Video Engine
│   └── src/

├── n8n/                     # [Config] Workflow Orchestration
│   ├── workflows/           # ✅ TRACK: JSON backup of workflows
│   └── .env                 # ❌ IGNORE: Secrets

├── visual/                  # [Mixed] ComfyUI & Models
│   ├── ComfyUI/             # ❌ IGNORE: The installation itself
│   └── workflows/           # ✅ TRACK: ComfyUI JSON workflows

├── assets/                  # [Assets]
│   ├── artists/             # 📦 LFS: Face anchors, voice samples
│   └── temp/                # ❌ IGNORE: Intermediate renders

├── .agent/                  # [Antigravity IDE]
│   └── workflows/           # ✅ TRACK: Agent workflow docs

└── scripts/                 # [Ops]
    └── setup_models.sh      # 📥 Symlink Strategy
```

---

## 2. 🛡️ The `.gitignore` (Updated for Docker)

```gitignore
# --- 1. System & Dependencies ---
.DS_Store
node_modules/
__pycache__/
.venv/
venv/
*.log
wget-log
*.pid

# --- 2. Secrets ---
.env
.env.*
sanity-studio/.sanity/
*private_key*

# --- 3. External Projects (Separate Repos) ---
external/BettaFish/
external/MediaCrawlerPro-Python/
external/MediaCrawlerPro-SignSrv/
external/Vidi/
CosyVoice/

# --- 4. Large Installations ---
visual/ComfyUI/
middleware/venv/

# --- 5. Database Persistence (Docker Volumes) ---
postgres/
redis/
mysql/
qdrant_storage/
n8n/binaryData/
n8n/git/
n8n/ssh/
n8n/config
n8n/nodes

# --- 6. Massive Assets ---
assets/models/
assets/temp/
outputs/
*.safetensors
*.ckpt
*.pth

# --- 7. Exceptions (Whitelist) ---
!assets/.gitkeep
!n8n/workflows/*.json
!docker/
```

---

## 3. 📦 Git LFS (Large File Storage)

```bash
# Initialize
git lfs install

# Configure Tracking (.gitattributes)
git lfs track "assets/artists/**/*.png"
git lfs track "assets/artists/**/*.wav"
git lfs track "assets/**/*.psd"

# Commit configuration
git add .gitattributes
```

---

## 4. 🐳 Docker Infrastructure as Code

Key files to always track:

| File | Purpose |
|------|---------|
| `docker-compose.yml` | All container definitions |
| `docker/mcn-core.Dockerfile` | Middleware + BettaFish container |
| `docker/requirements-core.txt` | Python dependencies |
| `start_mcn_os.sh` | Master startup script |

### Commit Docker Changes

```bash
git add docker-compose.yml docker/ start_mcn_os.sh
git commit -m "feat(docker): update container configuration"
```

---

## 5. 🧩 Low-Code Versioning

### ComfyUI Workflows
- **Location**: `visual/workflows/*.json`
- **Track**: JSON workflow files

### n8n Workflows
- **Location**: `n8n/workflows/*.json`
- **Track**: Exported workflow JSONs
- **Script**: Use n8n's export feature

### Antigravity Workflows
- **Location**: `.agent/workflows/*.md`
- **Track**: Agent documentation

---

## 6. 🔄 Common Git Commands

```bash
# Check status
git status

# Stage Docker changes
git add docker-compose.yml docker/

# Commit with conventional format
git commit -m "feat(docker): add ComfyUI container with profile"
git commit -m "fix(middleware): update Redis URL for auth"

# Push to GitHub
git push origin main
```

---

## 7. ⚠️ Important Notes

1. **External projects**: BettaFish, MediaCrawlerPro are separate repos/submodules
2. **Models**: Never commit .safetensors - use `scripts/setup_models.sh`
3. **Secrets**: All .env files are gitignored
4. **Docker volumes**: Database persistence folders are gitignored
