#!/bin/bash
mkdir -p /home/jimmy/Documents/mcn/assets/pretrained_models
cd /home/jimmy/Documents/mcn/assets/pretrained_models

echo "Downloading CosyVoice-300M-SFT..."
# Using git clone for reliability
git clone https://www.modelscope.cn/iic/CosyVoice-300M-SFT.git Fun-CosyVoice3-0.5B-2512

echo "Download complete."
ls -la Fun-CosyVoice3-0.5B-2512
