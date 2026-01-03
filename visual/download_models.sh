#!/bin/bash

# Function to download with retry
download_with_retry() {
    local url="$1"
    local dir="$2"
    local file="$3"
    
    echo "Downloading $file to $dir..."
    until aria2c -x 16 -s 16 -c -d "$dir" -o "$file" "$url"; do
        echo "Download of $file failed. Retrying in 5 seconds..."
        sleep 5
    done
    echo "$file download complete."
}

echo "Starting downloads..."

# Flux.1-Dev FP8 (16GB)
download_with_retry \
    "https://huggingface.co/Comfy-Org/flux1-dev/resolve/main/flux1-dev-fp8.safetensors" \
    "/home/jimmy/Documents/mcn/visual/ComfyUI/models/checkpoints" \
    "flux1-dev-fp8.safetensors"

# PuLID Flux
download_with_retry \
    "https://huggingface.co/guozinan/PuLID/resolve/main/pulid_flux_v0.9.0.safetensors" \
    "/home/jimmy/Documents/mcn/visual/ComfyUI/models/pulid" \
    "pulid_flux_v0.9.0.safetensors"

# Eva Clip
download_with_retry \
    "https://huggingface.co/Comfy-Org/sigclip_vision_patch14_384/resolve/main/sigclip_vision_patch14_384.safetensors" \
    "/home/jimmy/Documents/mcn/visual/ComfyUI/models/clip" \
    "eva_clip_l_14_336_fp16.safetensors"

echo "All downloads complete."
