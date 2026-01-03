from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from lib import redis_client

app = FastAPI(title="MCN GPU Scheduler (Async)", version="2.0")

class JobRequest(BaseModel):
    task_type: str       # "comfyui" | "cosyvoice"
    priority: int = 10   # 1 (Routine) | 100 (VIP)
    payload: Dict[str, Any]    # {"template": "flux_dev", "params": {...}}

@app.post("/submit_task")
def submit_job(job: JobRequest):
    """
    Enqueues a task for the background worker.
    Returns immediately with task_id.
    """
    # Validate payload for ComfyUI
    if job.task_type == "comfyui" and "template" not in job.payload:
         raise HTTPException(status_code=400, detail="ComfyUI task requires 'template' in payload")

    task_id = redis_client.enqueue_task(job.task_type, job.payload, job.priority)
    return {"status": "queued", "task_id": task_id}

@app.get("/status/{task_id}")
def check_status(task_id: str):
    info = redis_client.get_task_info(task_id)
    if not info:
        raise HTTPException(status_code=404, detail="Task not found")
    
    response = {
        "id": info["id"],
        "status": info["status"],
        "task_type": info["type"]
    }
    
    if info.get("result"):
        response["result"] = info["result"]
    
    if info.get("error"):
        response["error"] = info["error"]
        
    return response

@app.get("/health")
def health_check():
    return {"status": "ok", "mode": "async_worker"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
