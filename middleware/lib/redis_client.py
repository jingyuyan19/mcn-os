import redis
import json
import uuid
import os
import logging

logger = logging.getLogger("RedisClient")

# Connection
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)

QUEUE_VIP = "gpu_queue:vip"     # Priority 100
QUEUE_NORMAL = "gpu_queue:normal" # Priority 10
KEY_PREFIX = "task:info:"

def enqueue_task(task_type, params, priority=1):
    """Push task to appropriate queue."""
    task_id = str(uuid.uuid4())
    task_data = json.dumps({
        "id": task_id,
        "type": task_type,
        "params": params,
        "status": "queued",
        "result": None,
        "error": None
    })
    
    # 1. Store Task Info (TTL 24h)
    r.set(f"{KEY_PREFIX}{task_id}", task_data, ex=86400)

    # 2. Push to Queue
    if priority >= 100:
        r.rpush(QUEUE_VIP, task_id)
        logger.info(f"🚀 [VIP] Task {task_id} added to Fast Lane")
    else:
        r.rpush(QUEUE_NORMAL, task_id)
        logger.info(f"🌊 [Normal] Task {task_id} added to Slow Lane")
        
    return task_id

def get_next_task(timeout=5):
    """Blocking Pop from Queues (VIP first)."""
    # Keys are checked in order.
    task = r.blpop([QUEUE_VIP, QUEUE_NORMAL], timeout=timeout)
    
    if task:
        # task is (queue_name, value)
        return task[1].decode('utf-8')
    return None

def update_status(task_id, status, result=None, error=None):
    """Update task status in Redis."""
    key = f"{KEY_PREFIX}{task_id}"
    data = r.get(key)
    if data:
        task = json.loads(data)
        task['status'] = status
        if result: task['result'] = result
        if error: task['error'] = error
        r.set(key, json.dumps(task), ex=86400) # Reset TTL on update

def get_task_info(task_id):
    data = r.get(f"{KEY_PREFIX}{task_id}")
    return json.loads(data) if data else None
