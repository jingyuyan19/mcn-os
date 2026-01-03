#!/bin/bash
export CUDA_VISIBLE_DEVICES=0
cd /home/jimmy/Documents/mcn/visual/ComfyUI
source venv/bin/activate
echo "Starting ComfyUI on port 8188..."
python3 main.py --listen 0.0.0.0 --port 8188
