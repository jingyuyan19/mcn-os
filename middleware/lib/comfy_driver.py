import json
import requests
import websocket # type: ignore
import uuid
import os
import random
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("ComfyDriver")

# Configuration
COMFY_HOST = os.getenv("COMFY_HOST", "localhost")
COMFY_PORT = os.getenv("COMFY_PORT", "8188")
COMFY_URL = f"http://{COMFY_HOST}:{COMFY_PORT}"
WS_URL = f"ws://{COMFY_HOST}:{COMFY_PORT}/ws?clientId="

def free_vram():
    """💥 Force VRAM Purge."""
    try:
        requests.post(f"{COMFY_URL}/free", timeout=2)
        requests.post(f"{COMFY_URL}/unload_models", timeout=2)
        logger.info("🧹 VRAM Purged.")
    except Exception as e:
        logger.warning(f"⚠️ VRAM Clean Warning: {e}")

def execute_workflow(template_name, params):
    """Load template, inject params, execute via WebSocket."""
    
    # 1. Clean VRAM
    free_vram()

    # 2. Load Template
    client_id = str(uuid.uuid4())
    # Adjusted path to go up one level from lib/ to workflows/
    workflow_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "workflows", f"{template_name}.json")
    
    if not os.path.exists(workflow_path):
        raise FileNotFoundError(f"Workflow template not found: {workflow_path}")

    with open(workflow_path, 'r') as f:
        # ALWAYS read as string first for template injection
        workflow_str = f.read()
             
        # 2.1 String Replacement Injection
        for key, value in params.items():
             # Replace {{KEY}}
             placeholder = f"{{{{{key}}}}}"
             if placeholder in workflow_str:
                 workflow_str = workflow_str.replace(placeholder, str(value))
        
        try:
            workflow = json.loads(workflow_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse workflow after injection: {e}")
            raise ValueError(f"Invalid JSON in {template_name} after injection")

    # 3. Deep Parameter Injection (Dictionary Overlay)
    # params can also contain specific node overrides: {"3": {"inputs.steps": 50}}
    # We skipped this in the string replace version, but let's support it for advanced usage.
    # The 'params' dict passed here might mix "POSITIVE_PROMPT" (string replace) and "3" (node override).
    # Simple heuristic: if key is numeric string, it's a node override.
    for key, val in params.items():
        if key.isdigit() and key in workflow:
            # It's a node ID
            for field, field_val in val.items():
                # inputs.seed -> ["inputs"]["seed"]
                if "." in field:
                    parts = field.split(".")
                    target = workflow[key]
                    for part in parts[:-1]:
                        target = target.setdefault(part, {})
                    target[parts[-1]] = field_val
                else:
                    workflow[key].setdefault("inputs", {})[field] = field_val

    # 4. Random Seed Generation (if still a placeholder or not set)
    # Actually, ComfyUI needs a seed. If we injected it via string replace, good.
    # If not, let's look for KSampler and noise nodes.
    for node in workflow.values():
        if "inputs" in node and "seed" in node["inputs"]:
            # If seed is still a placeholder-ish string or we want to randomize?
            # Creating a random seed if it looks like a fixed default or was passed as 0/null
            # But usually we control this via params.
            pass

    # 5. WebSocket Connection
    ws = websocket.WebSocket()
    ws.connect(WS_URL + client_id)

    # 6. Queue Prompt
    payload = {"prompt": workflow, "client_id": client_id}
    res = requests.post(f"{COMFY_URL}/prompt", json=payload)
    if res.status_code != 200:
        raise RuntimeError(f"ComfyUI Error: {res.text}")
    
    prompt_id = res.json()['prompt_id']
    logger.info(f"Sent to ComfyUI: {prompt_id}")

    # 7. Wait for Completion
    output_files = []
    while True:
        out = ws.recv()
        if isinstance(out, str):
            msg = json.loads(out)
            # Execution finished for this prompt
            if msg['type'] == 'executing' and msg['data']['node'] is None and msg['data']['prompt_id'] == prompt_id:
                break
            # Output captured
            if msg['type'] == 'executed' and msg['data']['prompt_id'] == prompt_id:
                outputs = msg['data']['output']
                for nid, content in outputs.items():
                    for item in content.get('gifs', []) + content.get('images', []) + content.get('videos', []):
                         output_files.append(item) # Keep full item dict (filename, subfolder, type)
    
    ws.close()
    return output_files
