# middleware/lib/gpu_manager.py
"""
GPU Manager for MCN OS

Implements the "Anchored Tenant" strategy per Gemini Deep Think recommendation:
- CosyVoice (anchor): Always running, ~4GB VRAM
- Ollama (tenant A): Chat LLM, ~18-20GB VRAM
- ComfyUI (tenant B): Image generation, ~12-16GB VRAM

The GPUManager provides:
1. Redis-based GPU mutex lock
2. Active eviction of Ollama before ComfyUI tasks
3. Lock timeout for crash recovery
"""

import redis
import requests
import time
import os
from contextlib import contextmanager
from loguru import logger


class GPUManager:
    """Manages GPU lock and active eviction for VRAM sharing."""
    
    def __init__(self):
        """Initialize GPU manager with Redis connection."""
        # Redis URL format: redis://[:password@]host[:port]/[db]
        redis_url = os.getenv("REDIS_URL", "redis://:123456@redis:6379/0")
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.ollama_url = os.getenv("OLLAMA_URL", "http://ollama:11434")
        self.lock_key = "gpu_mutex"
        self.default_timeout = 300  # 5 minutes
    
    def force_unload_ollama(self, model: str = "qwen2.5:32b") -> bool:
        """
        Active preemption: tell Ollama to dump VRAM immediately.
        
        Sends keep_alive=0 to force immediate unload, overriding the
        default OLLAMA_KEEP_ALIVE=5m setting.
        
        Args:
            model: The model name to unload (default: qwen2.5:32b)
            
        Returns:
            bool: True if successful, False if Ollama not responding
        """
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={"model": model, "keep_alive": "0s"},
                timeout=10
            )
            logger.info(f"Ollama VRAM released for model {model}")
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama unload failed (may not be running): {e}")
            return False
    
    @contextmanager
    def acquire_gpu(self, service: str, timeout: int = None, evict_ollama: bool = False):
        """
        Context manager for GPU lock with optional active eviction.
        
        Args:
            service: Name of the service requesting GPU (e.g., "comfyui", "ollama")
            timeout: Lock timeout in seconds (default: 300)
            evict_ollama: If True, force unload Ollama before acquiring lock
            
        Yields:
            bool: True if lock acquired successfully
            
        Raises:
            Exception: If GPU lock is held by another service
            
        Example:
            with gpu_manager.acquire_gpu("comfyui", evict_ollama=True):
                # Run ComfyUI workflow
                pass
        """
        timeout = timeout or self.default_timeout
        
        # 1. If requesting for ComfyUI, evict Ollama first
        if evict_ollama or service == "comfyui":
            self.force_unload_ollama()
            time.sleep(1)  # Give NVIDIA driver time to reclaim VRAM
        
        # 2. Acquire lock (atomic set-if-not-exists with TTL)
        if self.redis.set(self.lock_key, service, nx=True, ex=timeout):
            try:
                logger.info(f"GPU lock acquired by {service}")
                yield True
            finally:
                # 3. Release only if we still own it
                if self.redis.get(self.lock_key) == service:
                    self.redis.delete(self.lock_key)
                    logger.info(f"GPU lock released by {service}")
        else:
            holder = self.redis.get(self.lock_key)
            raise Exception(f"GPU busy - held by {holder or 'unknown'}")
    
    def try_acquire_gpu(self, service: str, timeout: int = None) -> bool:
        """
        Non-blocking attempt to acquire GPU lock.
        
        Args:
            service: Name of the service requesting GPU
            timeout: Lock timeout in seconds
            
        Returns:
            bool: True if lock acquired, False otherwise
        """
        timeout = timeout or self.default_timeout
        return self.redis.set(self.lock_key, service, nx=True, ex=timeout)
    
    def release_gpu(self, service: str = None) -> bool:
        """
        Release GPU lock.
        
        Args:
            service: If provided, only release if this service holds the lock
            
        Returns:
            bool: True if lock was released
        """
        if service:
            if self.redis.get(self.lock_key) == service:
                return self.redis.delete(self.lock_key) > 0
            return False
        return self.redis.delete(self.lock_key) > 0
    
    def is_gpu_available(self) -> bool:
        """Check if GPU is available without blocking."""
        return not self.redis.exists(self.lock_key)
    
    def get_current_holder(self) -> str | None:
        """Get current GPU lock holder."""
        return self.redis.get(self.lock_key)
    
    def get_gpu_status(self) -> dict:
        """
        Get comprehensive GPU status.
        
        Returns:
            dict with keys: available, holder, ttl
        """
        holder = self.redis.get(self.lock_key)
        ttl = self.redis.ttl(self.lock_key) if holder else None
        
        return {
            "available": holder is None,
            "holder": holder,
            "ttl_seconds": ttl if ttl and ttl > 0 else None
        }


# Singleton instance
_gpu_manager = None

def get_gpu_manager() -> GPUManager:
    """Get or create the singleton GPUManager instance."""
    global _gpu_manager
    if _gpu_manager is None:
        _gpu_manager = GPUManager()
    return _gpu_manager
