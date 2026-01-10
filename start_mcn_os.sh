#!/bin/bash

# =============================================================================
# 🚀 MCN OS - Master Startup Script
# =============================================================================
# This script launches the entire AI Artist Operating System.
# It opens separate terminal tabs for each major component to allow log monitoring.
# =============================================================================

BASE_DIR="/home/jimmy/Documents/mcn"

# 1. Start/Check Docker Services (Background Infrastructure)
echo "🐳 Checking Docker Services..."
cd "$BASE_DIR"
docker-compose up -d
echo "✅ Docker Services are running (Perception, Brain, Storage)."

# 2. Launch Components in Separate Tabs
# We use gnome-terminal to keep logs visible for each service.

echo "🚀 Launching MCN OS Components..."

gnome-terminal --title="MCN Middleware" --tab --working-directory="$BASE_DIR/middleware" -- bash -c "
    echo '🧠 Starting Middleware API...';
    source venv/bin/activate;
    python3 server.py;
    exec bash"

gnome-terminal --title="ComfyUI (Universal)" --tab --working-directory="$BASE_DIR/visual/ComfyUI" -- bash -c "
    echo '🎨 Starting ComfyUI (Compatible with LTX-2, LongCat, GGUF)...';
    echo 'FLAGS: --cache-none --reserve-vram 2';
    source venv/bin/activate;
    export CUDA_VISIBLE_DEVICES=0;
    python3 main.py --listen 0.0.0.0 --port 8188 --cache-none --reserve-vram 2;
    exec bash"

gnome-terminal --title="Sanity Studio" --tab --working-directory="$BASE_DIR/sanity-studio" -- bash -c "
    echo '📝 Starting Sanity Content Studio...';
    npm run dev;
    exec bash"

echo "✨ MCN OS Startup Initiated!"
echo "   - Middleware: http://localhost:8000"
echo "   - ComfyUI:    http://localhost:8188"
echo "   - Sanity:     http://localhost:3333"
echo "   - n8n:        http://localhost:5678"
