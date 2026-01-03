#!/bin/bash
# Model Setup: The Symlink Strategy
# Ensures models are stored in 'assets/models' (Persistent)
# and linked to 'visual/ComfyUI/models' (Ephemeral)

ASSETS_ROOT="$(pwd)/assets/models"
COMFY_ROOT="$(pwd)/visual/ComfyUI/models"

# 1. Ensure Persistent Dirs Exist
mkdir -p "$ASSETS_ROOT/checkpoints"
mkdir -p "$ASSETS_ROOT/loras"
mkdir -p "$ASSETS_ROOT/unet"
mkdir -p "$ASSETS_ROOT/clip"
mkdir -p "$ASSETS_ROOT/vae"

# 2. Ensure ComfyUI Dirs Exist (in case it's a fresh install)
mkdir -p "$COMFY_ROOT/checkpoints"
mkdir -p "$COMFY_ROOT/loras"
mkdir -p "$COMFY_ROOT/unet"
mkdir -p "$COMFY_ROOT/clip"
mkdir -p "$COMFY_ROOT/vae"

# 3. Function to link and download
link_and_download() {
    TYPE=$1
    FILENAME=$2
    URL=$3
    
    SOURCE="$ASSETS_ROOT/$TYPE/$FILENAME"
    TARGET="$COMFY_ROOT/$TYPE/$FILENAME"
    
    # Symlink Check
    if [ ! -L "$TARGET" ]; then
        echo "🔗 Linking $TYPE/$FILENAME..."
        ln -sf "$SOURCE" "$TARGET"
    fi

    # Download Check
    if [ ! -f "$SOURCE" ]; then
        echo "⬇️ Downloading $FILENAME..."
        # Use huggingface-cli if available, else wget
        if command -v huggingface-cli &> /dev/null; then
             # This is a stub for HF CLI usage, falling back to wget for simplicity given current context
             wget -O "$SOURCE" "$URL"
        else
             wget -O "$SOURCE" "$URL"
        fi
    else
        echo "✅ Found $FILENAME in assets."
    fi
}

echo "=== 🏗️ Setting up Models (Symlink Mode) ==="

# --- Flux Dev (FP8) ---
link_and_download "checkpoints" "flux1-dev-fp8.safetensors" \
    "https://huggingface.co/Kiyss/Flux.1-dev-FP8/resolve/main/flux1-dev-fp8.safetensors"

# --- WanVideo (Example) ---
# Add your WanVideo URLs here
# link_and_download "checkpoints" "wan_video_1.3b.pth" "..."

echo "=== 🎉 Model Setup Complete ==="
echo "Models are safely stored in assets/models/ and linked to ComfyUI."
