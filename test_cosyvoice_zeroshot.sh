#!/bin/bash
# Test CosyVoice Zero Shot Inference
# Endpoint: /inference_zero_shot
# Requires: prompt_wav, prompt_text, tts_text

# Path to the found prompt wav (from host repo clone)
PROMPT_WAV="/home/jimmy/Documents/mcn/CosyVoice/asset/zero_shot_prompt.wav"

# Check if file exists
if [ ! -f "$PROMPT_WAV" ]; then
    echo "Error: Prompt wav not found at $PROMPT_WAV"
    exit 1
fi

echo "Testing CosyVoice Zero Shot..."
curl -X POST "http://localhost:50000/inference_zero_shot" \
  -F "tts_text=你好，我是你的AI数字员工。系统已成功上线。" \
  -F "prompt_text=Hope you can see our reference." \
  -F "prompt_wav=@$PROMPT_WAV" \
  --output active_test_output.wav \
  -v

echo "Done. Saved to active_test_output.wav"
