# MCN OS Quick Start Guide

**For AI Agents & Developers on a New Machine**

---

## Prerequisites

| Requirement | Version | Purpose |
|-------------|---------|---------|
| Ubuntu | 22.04+ | OS |
| Docker | 24.0+ | Containers |
| NVIDIA Driver | 535+ | GPU |
| CUDA | 12.x | GPU compute |
| Python | 3.10+ | Middleware |
| Node.js | 18+ | Remotion |
| Git LFS | 3.0+ | Large files |

---

## 1. Clone & Setup

```bash
# Clone repo
git clone https://github.com/jingyuyan19/mcn-os.git
cd mcn-os

# Pull LFS files
git lfs pull

# Create Python venv
cd middleware
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd ..

# Install Remotion deps
cd rendering
npm install
cd ..
```

---

## 2. Credentials Setup

### Required Secrets

| Secret | Where to Get | Where to Put |
|--------|--------------|--------------|
| Sanity Token | sanity.io/manage → API → Tokens | n8n credentials |
| DeepSeek API Key | platform.deepseek.com | n8n workflow header |
| HuggingFace Token | huggingface.co/settings/tokens | ComfyUI manager |

### Current Values (for reference)

```
Sanity Project ID: 4t6f8tmh
DeepSeek API: sk-4756665d490f43d59223ab9567be34c8
```

> ⚠️ **Security**: These are development keys. Rotate in production.

---

## 3. Download Models

Models are NOT in Git (too large). Download manually:

### Location
```
/mnt/data_ssd/ComfyUI/models/
# or symlink from ~/.cache/huggingface/
```

### Required Models

| Model | Size | HuggingFace Path |
|-------|------|------------------|
| Flux Dev BF16 | ~24GB | black-forest-labs/FLUX.1-dev |
| Flux VAE | ~335MB | included with Flux |
| WanVideo 1.3B | ~5GB | Wan-AI/wanvideo-1.3b |
| T5XXL | ~10GB | google/t5-xxl |
| CLIP L | ~246MB | openai/clip-vit-large |
| LongCat LoRA | ~150MB | (custom trained) |

### Download Script
```bash
./scripts/setup_models.sh
```

---

## 4. Start Services

```bash
# Start Docker containers (n8n, postgres, redis, nginx)
docker compose up -d

# Verify all running
docker ps

# Start ComfyUI (separate terminal)
cd /mnt/data_ssd/ComfyUI
python main.py --listen 0.0.0.0 --port 8188

# Start Middleware (separate terminal)
cd mcn
./start_middleware.sh
```

---

## 5. Verify Installation

```bash
# Check all services
docker ps                              # 4 containers running
curl localhost:5678                    # n8n UI
curl localhost:8000/health             # Middleware API
curl localhost:8081/assets/            # Nginx asset server
curl localhost:8188                    # ComfyUI

# Test end-to-end
# Import n8n/workflows/3_Orchestrator_V8_8.json
# Execute workflow → check assets/output/
```

---

## 6. Sanity Studio

```bash
cd sanity-studio
npm install
npm run dev
# Opens http://localhost:3333
```

---

## Common Issues on New Machine

| Issue | Solution |
|-------|----------|
| CUDA not found | Install NVIDIA driver + CUDA toolkit |
| Docker permission denied | `sudo usermod -aG docker $USER` |
| git lfs not found | `sudo apt install git-lfs` |
| Models missing | Run `./scripts/setup_models.sh` |
| n8n can't reach middleware | Use `172.17.0.1:8000` in Docker |

---

## Next Steps

After setup, refer to:
- `docs/README.md` → Documentation index
- `docs/CURRENT_STATE.md` → What's completed/next
- `docs/TROUBLESHOOTING.md` → Common issues
