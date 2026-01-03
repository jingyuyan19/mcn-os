"""
ComfyUI API Client
Wraps ComfyUI's built-in REST API for workflow execution.
"""
import requests
import logging
import time

logger = logging.getLogger("ComfyClient")

class ComfyClient:
    def __init__(self, host="localhost", port=8188):
        self.base_url = f"http://{host}:{port}"
        
    def queue_prompt(self, workflow: dict, client_id: str = "mcn_middleware") -> dict:
        """
        Submit a workflow to ComfyUI for execution.
        
        Args:
            workflow: ComfyUI workflow JSON
            client_id: Unique client identifier for tracking
        
        Returns:
            Response with prompt_id for tracking
        """
        payload = {
            "prompt": workflow,
            "client_id": client_id
        }
        
        try:
            resp = requests.post(f"{self.base_url}/prompt", json=payload, timeout=30)
            resp.raise_for_status()
            result = resp.json()
            logger.info(f"Prompt queued: {result.get('prompt_id', 'unknown')}")
            return result
        except requests.RequestException as e:
            logger.error(f"Failed to queue prompt: {e}")
            raise
    
    def get_history(self, prompt_id: str) -> dict:
        """Get the execution history for a prompt."""
        try:
            resp = requests.get(f"{self.base_url}/history/{prompt_id}", timeout=10)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            logger.error(f"Failed to get history: {e}")
            raise
    
    def wait_for_completion(self, prompt_id: str, timeout: int = 300, poll_interval: float = 2.0) -> dict:
        """
        Poll until the prompt is completed or timeout.
        
        Returns:
            History entry for the completed prompt.
        """
        start = time.time()
        while time.time() - start < timeout:
            history = self.get_history(prompt_id)
            if prompt_id in history:
                entry = history[prompt_id]
                if entry.get("status", {}).get("completed"):
                    logger.info(f"Prompt {prompt_id} completed.")
                    return entry
            time.sleep(poll_interval)
        
        raise TimeoutError(f"Prompt {prompt_id} did not complete within {timeout}s")
    
    def get_output_images(self, history_entry: dict) -> list:
        """Extract output image paths from a history entry."""
        outputs = []
        for node_id, node_output in history_entry.get("outputs", {}).items():
            if "images" in node_output:
                for img in node_output["images"]:
                    outputs.append({
                        "filename": img.get("filename"),
                        "subfolder": img.get("subfolder", ""),
                        "type": img.get("type", "output")
                    })
        return outputs

# Example usage
if __name__ == "__main__":
    client = ComfyClient()
    # Test connection
    try:
        resp = requests.get("http://localhost:8188/object_info", timeout=5)
        print("ComfyUI is accessible.")
    except requests.RequestException:
        print("ComfyUI is not running or not accessible.")
