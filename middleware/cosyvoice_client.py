"""
CosyVoice API Client
Wrapper for CosyVoice 3.0 FastAPI endpoints.
"""
import requests
import wave
import logging
import os

logger = logging.getLogger("CosyVoiceClient")

class CosyVoiceClient:
    def __init__(self, host="localhost", port=50000):
        self.base_url = f"http://{host}:{port}"
        
    def inference_zero_shot(self, tts_text: str, prompt_text: str, prompt_wav_path: str, output_path: str) -> dict:
        """
        Call CosyVoice zero-shot inference and save result to output_path.
        
        Args:
            tts_text: Text to synthesize.
            prompt_text: "System prompt<|endofprompt|>Reference text" for CosyVoice3.
            prompt_wav_path: Path to reference audio file.
            output_path: Where to save the generated WAV file.
            
        Returns:
            Dict with status and output path.
        """
        url = f"{self.base_url}/inference_zero_shot"
        
        try:
            if not os.path.exists(prompt_wav_path):
                raise FileNotFoundError(f"Prompt audio not found: {prompt_wav_path}")
                
            payload = {
                'tts_text': tts_text,
                'prompt_text': prompt_text
            }
            
            # Open file in binary mode
            with open(prompt_wav_path, 'rb') as f:
                files = [('prompt_wav', ('prompt.wav', f, 'audio/wav'))]
                
                logger.info(f"Sending request to {url}...")
                response = requests.post(url, data=payload, files=files, stream=True, timeout=120)
                
                if response.status_code != 200:
                    raise requests.RequestException(f"API Error {response.status_code}: {response.text}")
                
                # Collect audio data (raw PCM)
                audio_data = b''
                for chunk in response.iter_content(chunk_size=16000):
                    audio_data += chunk
                
                # Save as WAV
                # CosyVoice outputs 22050Hz mono int16 raw PCM
                with wave.open(output_path, 'wb') as wav_file:
                    wav_file.setnchannels(1)
                    wav_file.setsampwidth(2)
                    wav_file.setframerate(22050)
                    wav_file.writeframes(audio_data)
                    
                logger.info(f"Generated audio saved to {output_path} ({len(audio_data)} bytes)")
                
                return {
                    "status": "success",
                    "output_path": output_path,
                    "bytes": len(audio_data)
                }
                
        except Exception as e:
            logger.error(f"CosyVoice inference failed: {e}")
            raise
