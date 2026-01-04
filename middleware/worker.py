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
        params = info.get('params', {})
        logger.info(f"▶️ Processing: {task_type} (ID: {task_id})")
        redis_client.update_status(task_id, "processing")

        success = False
        result_data = {}
        
        # 3. Route & Execute
        if task_type == "comfyui": # Keeping original comfyui handler for now
            result_data = process_comfy(task_id, params)
            success = True
        elif task_type == "comfyui_workflow": # New comfyui_workflow handler
            # This assumes 'workflow_json' is directly in params, or 'template' is used.
            # Adjust based on actual 'comfy_driver.execute_workflow' signature.
            # For now, let's assume it uses 'template' and 'params' like process_comfy.
            # If workflow_json is expected, it needs to be passed in 'params'.
            template_name = params.get("template")
            if not template_name:
                raise ValueError("Task params missing 'template' for comfyui_workflow")
            
            injection_params = params.get("params", {})
            
            # Inject comfy_host if needed, though comfy_driver usually handles this internally
            # params["comfy_host"] = f"{os.getenv('COMFY_HOST', 'localhost')}:{os.getenv('COMFY_PORT', '8188')}"
            
            files = comfy_driver.execute_workflow(template_name, injection_params)
            result_data = {"files": files}
            success = True
            
        elif task_type == "cosyvoice":
            # For CosyVoice, we might also want to purge VRAM if we are really tight,
            # but usually it's smaller. Let's start with just running it.
            # comfy_driver.free_vram() # Optional: Kill Comfy before Cosy
            result_data = process_cosy(task_id, params)
            success = True
        elif task_type == "remotion_render":
            from lib.remotion_driver import execute_render
            # Params: timeline (json), output_path
            timeline = params.get("timeline")
            if not timeline:
                raise ValueError("Remotion render task missing 'timeline'")
            
            output_filename = params.get("output_filename", f"render_{task_id}.mp4")
            
            # Ensure assets/output directory exists (Project Root)
            # Worker CWD is 'middleware', so we go up one level
            output_dir = os.path.abspath(os.path.join(os.getcwd(), "../assets/output"))
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, output_filename)
            
            success = execute_render(timeline, output_path)
            if success:
                # Return relative path for asset server
                result_data = {"video_path": f"/assets/output/{output_filename}"}
            else:
                result_data = {"error": "Render failed, check worker logs"}
        else:
            logger.error(f"Unknown task type: {task_type}")
            success = False
            result_data = {"error": f"Unknown task type: {task_type}"}

        # 4. Success / Completion
        if success:
            redis_client.update_status(task_id, "completed", result=result_data)
            logger.info(f"✅ Done: {task_type} {task_id}")
        else:
            # If success is False but no exception was raised (e.g., remotion_render failed internally)
            redis_client.update_status(task_id, "failed", error=result_data.get("error", "Task failed without specific error message"))
            logger.error(f"❌ Task failed: {task_type} {task_id} - {result_data.get('error', 'Unknown error')}")

    except Exception as e:
        logger.error(f"❌ Error processing {task_id}: {e}")
        traceback.print_exc()
        redis_client.update_status(task_id, "failed", error=str(e))

