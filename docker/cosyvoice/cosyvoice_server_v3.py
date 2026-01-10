# Copyright (c) 2024 Alibaba Inc (authors: Xiang Lyu)
# Fixed for CosyVoice3 - uses temp files, simple generate_data
# DO NOT delete temp files until after streaming completes
import os
import sys
import argparse
import logging
import tempfile
logging.getLogger('matplotlib').setLevel(logging.WARNING)
from fastapi import FastAPI, UploadFile, Form, File
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import numpy as np
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append('{}/../../..'.format(ROOT_DIR))
sys.path.append('{}/../../../third_party/Matcha-TTS'.format(ROOT_DIR))
from cosyvoice.cli.cosyvoice import CosyVoice, CosyVoice2, CosyVoice3
from cosyvoice.utils.file_utils import load_wav

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"])


def save_upload_to_temp(upload_file: UploadFile) -> str:
    """Save uploaded file to temp location and return path.
    Uses shutil to properly copy the SpooledTemporaryFile content."""
    import shutil
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp_path = tmp.name
    tmp.close()  # Close so we can write to it
    
    # Reset file position and copy content
    upload_file.file.seek(0)
    with open(tmp_path, 'wb') as f:
        shutil.copyfileobj(upload_file.file, f)
    
    return tmp_path


def generate_data(model_output):
    """Original CosyVoice generate_data - streams raw PCM bytes"""
    for i in model_output:
        tts_audio = (i['tts_speech'].numpy() * (2 ** 15)).astype(np.int16).tobytes()
        yield tts_audio


@app.get("/inference_sft")
@app.post("/inference_sft")
async def inference_sft(tts_text: str = Form(), spk_id: str = Form()):
    model_output = cosyvoice.inference_sft(tts_text, spk_id)
    return StreamingResponse(generate_data(model_output))


@app.get("/inference_zero_shot")
@app.post("/inference_zero_shot")
async def inference_zero_shot(tts_text: str = Form(), prompt_text: str = Form(), prompt_wav: UploadFile = File()):
    # Save uploaded file to temp (CosyVoice3 frontend needs file path)
    prompt_path = save_upload_to_temp(prompt_wav)
    
    # CRITICAL: CosyVoice3 requires <|endofprompt|> token
    # Check if we are using CosyVoice3 and append if missing
    if cosyvoice.__class__.__name__ == 'CosyVoice3' and '<|endofprompt|>' not in prompt_text:
        prompt_text += ' <|endofprompt|>'
        
    model_output = cosyvoice.inference_zero_shot(tts_text, prompt_text, prompt_path)
    # Note: Don't delete temp file here - generator hasn't consumed it yet
    # Temp files in /tmp are cleaned up by OS
    return StreamingResponse(generate_data(model_output))


@app.get("/inference_cross_lingual")
@app.post("/inference_cross_lingual")
async def inference_cross_lingual(tts_text: str = Form(), prompt_wav: UploadFile = File()):
    prompt_path = save_upload_to_temp(prompt_wav)
    model_output = cosyvoice.inference_cross_lingual(tts_text, prompt_path)
    return StreamingResponse(generate_data(model_output))


@app.get("/inference_instruct")
@app.post("/inference_instruct")
async def inference_instruct(tts_text: str = Form(), spk_id: str = Form(), instruct_text: str = Form()):
    model_output = cosyvoice.inference_instruct(tts_text, spk_id, instruct_text)
    return StreamingResponse(generate_data(model_output))


@app.get("/inference_instruct2")
@app.post("/inference_instruct2")
async def inference_instruct2(tts_text: str = Form(), instruct_text: str = Form(), prompt_wav: UploadFile = File()):
    prompt_path = save_upload_to_temp(prompt_wav)
    model_output = cosyvoice.inference_instruct2(tts_text, instruct_text, prompt_path)
    return StreamingResponse(generate_data(model_output))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=50000)
    parser.add_argument('--model_dir', type=str, default='iic/CosyVoice-300M',
                        help='local path or modelscope repo id')
    args = parser.parse_args()
    try:
        cosyvoice = CosyVoice(args.model_dir)
    except Exception:
        try:
            cosyvoice = CosyVoice2(args.model_dir)
        except Exception:
            try:
                cosyvoice = CosyVoice3(args.model_dir)
            except Exception:
                raise TypeError('no valid model_type!')
    uvicorn.run(app, host="0.0.0.0", port=args.port)
