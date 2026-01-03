#!/bin/bash
# Reinstall Custom Nodes (Disaster Recovery)
# Clones essential plugins that might be missing after a fresh clone.

NODES_DIR="./visual/ComfyUI/custom_nodes"
mkdir -p $NODES_DIR

install_node() {
    REPO_URL=$1
    DIR_NAME=$(basename $REPO_URL .git)
    TARGET="$NODES_DIR/$DIR_NAME"
    
    if [ -d "$TARGET" ]; then
        echo "✅ $DIR_NAME already exists. Pulling latest..."
        cd "$TARGET" && git pull && cd - > /dev/null
    else
        echo "⬇️ Cloning $DIR_NAME..."
        git clone "$REPO_URL" "$TARGET"
    fi
}

echo "=== 🔌 Restoring ComfyUI Custom Nodes ==="

# 1. Manager (The most important one)
install_node "https://github.com/ltdrdata/ComfyUI-Manager.git"

# 2. Video Helper Suite (For video load/save)
install_node "https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git"

# 3. PuLID (Face ID)
install_node "https://github.com/ToTheBeginning/ComfyUI-PuLID.git"

# 4. WanVideo Wrapper (Video Gen)
install_node "https://github.com/kijai/ComfyUI-WanVideoWrapper.git"

# 5. GGUF Support (If needed for low vram)
# install_node "https://github.com/City96/ComfyUI-GGUF.git"

echo "=== 🎉 Node Restoration Complete ==="
echo "Please restart ComfyUI to load new nodes."
