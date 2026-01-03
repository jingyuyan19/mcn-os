import redis
import time
import logging

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LockManager")

class GPULockManager:
    def __init__(self, redis_host='localhost', redis_port=6379, db=0):
        self.r = redis.Redis(host=redis_host, port=redis_port, db=db, decode_responses=True)
        self.QUEUE_HIGH = "gpu_queue_high"
        self.QUEUE_LOW = "gpu_queue_low"
        self.GPU_TOKEN_KEY = "gpu_active_token"
        
        # Ensure token key exists (reset on init if needed, or handle manually)
        # In a real system, we might not want to reset on every restart.
        
    def acquire_lock(self, priority: int, task_id: str, timeout: int = 60) -> bool:
        """
        Attempt to acquire the GPU lock.
        If priority >= 100, attempts to jump queue or preempt (logic simplified for now).
        """
        logger.info(f"Task {task_id} requesting lock with priority {priority}...")
        
        # 1. Check if GPU is free
        # Simple Mutex implementation using Redis 'setnx' with expiry for safety
        # But we need a QUEUE system as per requirements.
        
        # Add to appropriate list
        if priority >= 100:
            self.r.lpush(self.QUEUE_HIGH, task_id) # High prio goes to front? Or separate queue? 
            # Separate queue is better for explicit "Speed 2" logic.
        else:
            self.r.rpush(self.QUEUE_LOW, task_id)
            
        # 2. Blocking Wait for Token
        # This part needs a worker to process? 
        # Or does the client block?
        # "Middleware Service" should handle the blocking.
        
        # FOR PHASE 3.1 (Basic Unit):
        # We will implement a simple 'try_acquire' that the API usage loop calls.
        
        # Real logic:
        # The Scheduler (Worker) pops from High, then Low.
        # If item found, it 'grants' the lock.
        
        return True

    def release_lock(self, task_id: str):
        logger.info(f"Task {task_id} releasing lock...")
        self.r.delete(self.GPU_TOKEN_KEY)
