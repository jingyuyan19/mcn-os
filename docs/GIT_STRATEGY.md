# Digital MCN OS - Hybrid Monorepo Strategy (Refined)

**Goal**: A sustainable version control system for a project mixing Production Code (TS/Python), Low-Code (n8n/ComfyUI), and Huge Assets (Models/Video).

**Core Philosophy**: "Code in Git, Logic in JSON, Models in Scripts, Assets in LFS."

---

## 1. 📂 Validated Directory Structure

We will adapt your current working directory `/home/jimmy/Documents/mcn` to be the Git Root.

```text
/home/jimmy/Documents/mcn/  (Git Root)
├── .git/
├── .gitignore               <-- 🛡️ Vital: Ignores 10GB+ folders
├── .gitattributes           <-- 📦 LFS: Handles binary assets
├── docker-compose.yml       <-- Infra as Code
├── README.md

├── middleware/              # [Code] Python GPU Orchestration (FastAPI)
│   ├── src/                 # (Move server.py key files here?)
│   ├── workflows/           # ✅ TRACK: API JSONs for machine execution
│   └── requirements.txt
│
├── sanity-studio/           # [Code] CMS Control Plane
│   ├── schemaTypes/
│   └── sanity.config.ts
│
├── rendering/               # [Code] Remotion Video Engine
│   └── src/
│
├── n8n/                     # [Config] Workflow Orchestration
│   ├── workflows/           # ✅ TRACK: JSON backup of workflows
│   └── .env                 # ❌ IGNORE: Secrets
│
├── visual/                  # [Mixed] ComfyUI & Models
│   ├── ComfyUI/             # ❌ IGNORE: The installation itself
│   └── workflows/           # ✅ TRACK: "Source Code" for ComfyUI (UI Format)
│       ├── flux_dev.json
│       └── wan_dev.json
│
├── assets/                  # [Assets]
│   ├── artists/             # 📦 LFS: Face anchors, voice samples
│   ├── models/              # ❌ IGNORE: Checkpoints (Script it!)
│   └── temp/                # ❌ IGNORE: Intermediate renders
│
└── scripts/                 # [Ops]
    ├── setup_models.sh      # 📥 Symlink Strategy (Persistent Storage)
    ├── setup_nodes.sh       # 🔌 Plugin Snapshot (Git Clone)
    └── backup_n8n.sh        # 🔄 Dump n8n DB to JSON (Granular)
```

---

## 2. 🛡️ The `.gitignore` Shield

Create this file immediately to prevent accidental commits of massive files.

```gitignore
# --- 1. System & Dependencies ---
.DS_Store
node_modules/
__pycache__/
.venv/
venv/
*.log
wget-log

# --- 2. Secrets ---
.env
sanity-studio/.sanity/
*private_key*

# --- 3. Massive Installations (Repo-in-Repo) ---
visual/ComfyUI/       # Ignored entirely! We rebuild via setup_nodes.sh
CosyVoice/
visual/active_test_output.wav

# --- 4. Database Persistence (Docker Volumes) ---
postgres/
redis/
n8n/binaryData/
n8n/git/
n8n/ssh/
n8n/config
n8n/nodes

# --- 5. Massive Assets ---
# We track specific assets via LFS, ignore the rest
assets/models/
assets/temp/
outputs/
*.safetensors
*.ckpt
*.pth

# --- 6. Exceptions (Whitelist) ---
!assets/.gitkeep
!n8n/workflows/*.json
```

---

## 3. 📦 Git LFS (Large File Storage)

Don't bloat the repo history. Store pointers instead of blobs.

```bash
# Initialize
git lfs install

# Configure Tracking (.gitattributes)
git lfs track "assets/artists/**/*.png"
git lfs track "assets/artists/**/*.wav"
git lfs track "assets/sponsorships/**/*.pdf"
git lfs track "assets/**/*.psd"
git lfs track "assets/**/*.ai"

# Commit configuration
git add .gitattributes
```

---

## 4. 🧩 Low-Code Versioning Workflow

### A. ComfyUI (The "Source vs Build" problem)
ComfyUI workflows are code.
*   **Action**: Create `visual/workflows/` directory.
*   **Source Truth**: `visual/workflows/[name]_edit.json` (The .json with UI nodes)
*   **Build Truth**: `middleware/workflows/[name]_api.json` (The API export for automation)
*   **Plugins**: Managed via `scripts/setup_nodes.sh`.

### B. n8n (The Database problem)
n8n workflows live in SQLite.
*   **Strategy**: Granular Backup.
*   **Script**: `scripts/backup_n8n.sh` generates individual JSON files for each workflow.
*   **Commit**: `n8n/workflows/*.json`

---

## 5. 🐘 Model Management (Symlink Strategy)

We separate **Asset Persistence** from **Runtime Execution**.

1.  **Storage**: `assets/models/checkpoints/` (Persistent, ignored)
2.  **Runtime**: `visual/ComfyUI/models/checkpoints/` (ignored)
3.  **Link**: `scripts/setup_models.sh` creates the symlink.

If you wipe `visual/ComfyUI`, your models are safe in `assets/models`.

