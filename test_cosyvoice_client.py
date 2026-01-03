#!/usr/bin/env python3
"""
CosyVoice Zero-Shot Test Client
Properly saves raw PCM audio stream as valid WAV file
"""
import requests
import wave
import struct
import sys

# API endpoint
URL = "http://localhost:50000/inference_zero_shot"
PROMPT_WAV = "/home/jimmy/Documents/mcn/CosyVoice/asset/zero_shot_prompt.wav"
OUTPUT_WAV = "/home/jimmy/Documents/mcn/assets/cosyvoice_test_output.wav"

# TTS parameters
TTS_TEXT = "你好，我是你的AI数字员工。系统已成功上线。"
# CosyVoice3 format: system prompt + <|endofprompt|> + text matching the reference audio
PROMPT_TEXT = "You are a helpful assistant.<|endofprompt|>希望你以后能够做的比我还好呦。"

# Audio parameters (CosyVoice outputs 22050Hz mono int16)
SAMPLE_RATE = 22050
CHANNELS = 1
SAMPLE_WIDTH = 2  # 16-bit = 2 bytes

def main():
    print(f"Testing CosyVoice Zero-Shot...")
    print(f"Input text: {TTS_TEXT}")
    
    # Prepare request
    payload = {
        'tts_text': TTS_TEXT,
        'prompt_text': PROMPT_TEXT
    }
    files = [('prompt_wav', ('prompt.wav', open(PROMPT_WAV, 'rb'), 'audio/wav'))]
    
    # Make streaming request
    response = requests.post(URL, data=payload, files=files, stream=True)
    
    if response.status_code != 200:
        print(f"Error: HTTP {response.status_code}")
        print(response.text)
        sys.exit(1)
    
    # Collect all audio chunks
    audio_data = b''
    for chunk in response.iter_content(chunk_size=16000):
        audio_data += chunk
    
    print(f"Received {len(audio_data)} bytes of audio data")
    
    # Save as proper WAV file
    with wave.open(OUTPUT_WAV, 'wb') as wav_file:
        wav_file.setnchannels(CHANNELS)
        wav_file.setsampwidth(SAMPLE_WIDTH)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(audio_data)
    
    print(f"Saved to: {OUTPUT_WAV}")
    
    # Verify the file
    with wave.open(OUTPUT_WAV, 'rb') as wav_file:
        duration = wav_file.getnframes() / wav_file.getframerate()
        print(f"Duration: {duration:.2f} seconds")
        print(f"Channels: {wav_file.getnchannels()}")
        print(f"Sample rate: {wav_file.getframerate()} Hz")

if __name__ == "__main__":
    main()
