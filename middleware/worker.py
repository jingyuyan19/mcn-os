import time
import os
import logging
import traceback
from lib import redis_client
from lib import comfy_driver
# Renaming/Importing the class from the file we copied
from lib.cosy_driver import CosyVoiceClient

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("GPUWorker")

# Initialize Clients
cosy_client = CosyVoiceClient(host="localhost", port=50000)
OUTPUT_DIR = "/home/jimmy/Documents/mcn/outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

logger.info("👷 GPU Worker Started... Waiting for jobs.")

def process_comfy(task_id, params):
    """Handle ComfyUI Task"""
    template_name = params.get("template")
    if not template_name:
        raise ValueError("Task params missing 'template'")
    
    # params['params'] contains the actual injection values
    injection_params = params.get("params", {})
    logger.info(f"Worker processing params: {injection_params}")
    
    files = comfy_driver.execute_workflow(template_name, injection_params)
    return {"files": files}

def process_cosy(task_id, params):
    """Handle CosyVoice Task"""
    output_path = os.path.join(OUTPUT_DIR, f"{task_id}.wav")
    
    resp = cosy_client.inference_zero_shot(
        tts_text=params.get('tts_text'),
        prompt_text=params.get('prompt_text'),
        prompt_wav_path=params.get('prompt_wav_path'),
        output_path=output_path
    )
    return resp

while True:
    # 1. Fetch Task (Blocking Wait)
    try:
        task_id = redis_client.get_next_task(timeout=5)
    except Exception as e:
        logger.error(f"Redis Connection Error: {e}")
        time.sleep(5)
        continue

    if not task_id:
        continue 

    try:
        # 2. Get Details
        info = redis_client.get_task_info(task_id)
        if not info:
            logger.warning(f"Task {task_id} not found in info store.")
            continue

        task_type = info['type']
        logger.info(f"▶️ Processing: {task_type} (ID: {task_id})")
        redis_client.update_status(task_id, "processing")

        result = None
        
        # 3. Route & Execute
        if task_type == "comfyui":
            result = process_comfy(task_id, info['params'])
        elif task_type == "cosyvoice":
            # For CosyVoice, we might also want to purge VRAM if we are really tight,
            # but usually it's smaller. Let's start with just running it.
            # comfy_driver.free_vram() # Optional: Kill Comfy before Cosy
            result = process_cosy(task_id, info['params'])
        else:
            raise ValueError(f"Unknown task type: {task_type}")

        # 4. Success
        redis_client.update_status(task_id, "completed", result=result)
        logger.info(f"✅ Done: {task_type} {task_id}")

    except Exception as e:
        logger.error(f"❌ Error processing {task_id}: {e}")
        traceback.print_exc()
        redis_client.update_status(task_id, "failed", error=str(e))
