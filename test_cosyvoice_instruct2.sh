#!/bin/bash
# CosyVoice3 Zero-Shot Test
# Uses instruct2 endpoint with file upload
# CosyVoice3 API expects file path, so we pass the file via multipart form

PROMPT_WAV="/home/jimmy/Documents/mcn/CosyVoice/asset/zero_shot_prompt.wav"

echo "Testing CosyVoice3 inference_instruct2..."
curl -X POST "http://localhost:50000/inference_instruct2" \
  -F "tts_text=你好，我是你的AI数字员工。系统已成功上线。" \
  -F "instruct_text=You are a helpful assistant.<|endofprompt|>" \
  -F "prompt_wav=@$PROMPT_WAV" \
  --output /home/jimmy/Documents/mcn/assets/cosyvoice_instruct2_output.wav \
  -w "\nHTTP Status: %{http_code}\n"

echo "Saved to assets/cosyvoice_instruct2_output.wav"
ls -la /home/jimmy/Documents/mcn/assets/cosyvoice_instruct2_output.wav
