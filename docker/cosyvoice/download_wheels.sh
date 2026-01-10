#!/bin/bash
# download_wheels.sh (Deep Think Final Solution)

BASE_DIR="/home/jimmy/Documents/mcn/docker/cosyvoice/packages/offline"
mkdir -p "$BASE_DIR"
cd "$BASE_DIR"

echo "📂 Final Mule Download (Using Official PyPI with Proxy)..."

# 1. Download the MISSING nvidia-cublas-cu12 from OFFICIAL PyPI
echo "⬇️  Downloading nvidia-cublas-cu12 from official PyPI..."
pip download nvidia-cublas-cu12 \
    --index-url https://pypi.org/simple \
    --proxy http://127.0.0.1:7897 \
    --no-deps \
    --dest .

# 2. Download nvidia-cuda-runtime-cu12 (safeguard dependency)
echo "⬇️  Downloading nvidia-cuda-runtime-cu12..."
pip download nvidia-cuda-runtime-cu12 \
    --index-url https://pypi.org/simple \
    --proxy http://127.0.0.1:7897 \
    --no-deps \
    --dest .

# 3. Verify we have all NVIDIA wheels
echo ""
echo "✅ Verify the 'Big Three' NVIDIA wheels:"
ls -lh nvidia*.whl

echo ""
echo "📌 You should see:"
echo "   nvidia_cudnn_cu12... (~618MB)"
echo "   nvidia_cublas_cu12... (~581MB) ← NEW"
echo "   nvidia_cuda_runtime.. (~3MB) ← NEW"
