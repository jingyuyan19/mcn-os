#!/bin/bash
echo "Testing CosyVoice API..."

curl -v -X POST "http://localhost:50000/inference/sft" \
     -H "Content-Type: application/json" \
     -d '{
           "tts_text": "我是MCN系统的第一位数字艺人，很高兴见到大家。",
           "spk_id": "中文女",
           "prompt_text": "",
           "prompt_wav_upload_url": ""
         }' \
     --output output.wav

echo "Done. Generated output.wav"
