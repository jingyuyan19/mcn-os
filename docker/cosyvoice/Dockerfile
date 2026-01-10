# Dockerfile.golden - Clean VPN Build (Deep Think Final)
# Base Image: PyTorch 2.1 with CUDA 12.1
FROM pytorch/pytorch:2.1.2-cuda12.1-cudnn8-devel

ENV TORCH_CUDA_ARCH_LIST="8.9" \
    CUDA_HOME=/usr/local/cuda \
    DEBIAN_FRONTEND=noninteractive \
    MAX_JOBS=4

WORKDIR /opt/CosyVoice

# 1. System Dependencies
# With VPN, we don't need to swap mirrors. Standard Ubuntu works.
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl ffmpeg libsox-dev build-essential \
    && rm -rf /var/lib/apt/lists/*

# 2. Copy Source Code
COPY CosyVoice /opt/CosyVoice

# 3. Install Python Dependencies (The "Golden" Stack)
# We use standard pip, which will route through your VPN
RUN pip install --upgrade pip

# Clean requirements to avoid conflicts
RUN sed -i '/onnxruntime/d' requirements.txt && \
    sed -i '/tensorrt/d' requirements.txt && \
    sed -i '/transformers/d' requirements.txt

# Install the exact versions that fix the "Trembling" audio
# This downloads ~1.5GB, but your VPN should handle it
RUN pip install --no-cache-dir \
    onnxruntime-gpu==1.19.2 \
    nvidia-cudnn-cu12 \
    nvidia-cublas-cu12 \
    transformers==4.51.3 \
    modelscope

# Install remaining requirements
RUN pip install --no-cache-dir -r requirements.txt

# Fix ruamel-yaml version for hyperpyyaml compatibility + add missing deps
RUN pip install --no-cache-dir "ruamel.yaml<0.18" x-transformers

# 4. Apply The Fixes
# Fix A: Point System to the NEW pip-installed cuDNN 9 libraries
ENV LD_LIBRARY_PATH=/opt/conda/lib/python3.10/site-packages/nvidia/cudnn/lib:/opt/conda/lib/python3.10/site-packages/nvidia/cublas/lib:/usr/local/cuda/lib64:$LD_LIBRARY_PATH

# Fix B: Patch Solver Steps to 50
RUN grep -rl "n_timesteps" . | xargs -r sed -i 's/n_timesteps=[0-9]*/n_timesteps=50/g'

ENV PYTHONPATH=/opt/CosyVoice

CMD ["python3", "runtime/python/fastapi/server.py", "--port", "50000", "--model_dir", "/models/Fun-CosyVoice3-0.5B-2512"]
