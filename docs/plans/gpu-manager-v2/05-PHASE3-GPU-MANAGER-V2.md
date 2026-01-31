# Phase 3: GPU Manager V2

**Risk Level**: Medium
**Dependencies**: Phase 1 (VRAM Tracking), Phase 2 (Lifecycle Manager)
**Estimated Effort**: 2 days

## Overview

Create the unified GPU Manager V2 that integrates VRAM tracking, lifecycle management, and pipeline-phase orchestration.

## Prerequisites

- Phase 1 complete (VRAM Tracker)
- Phase 2 complete (Lifecycle Manager)
- Redis available for distributed locking

## Step 3.1: Create GPU Manager V2

**File**: `middleware/lib/gpu_manager_v2.py`

```python
"""
GPU Manager V2 - Comprehensive GPU Resource Management for MCN OS.

Extends the original gpu_manager.py with:
- Real-time VRAM tracking via pynvml
- Service lifecycle management (Docker + Native)
- Pipeline-phase-aware scheduling
- Priority-based preemption

Usage:
    from lib.gpu_manager_v2 import get_gpu_manager_v2

    manager = get_gpu_manager_v2()

    # Prepare for pipeline phase (stops/starts services automatically)
    await manager.prepare_for_phase(4)  # Video generation

    # Or use specific service with locking
    async with manager.use_service("comfyui") as ready:
        if ready:
            result = comfy_driver.execute_workflow(...)

    # Get status
    status = await manager.get_status()
"""
import asyncio
import redis
import os
from typing import Optional, Dict, List
from contextlib import asynccontextmanager
from loguru import logger

from .vram_tracker import VRAMTracker, VRAMStatus, get_vram_tracker
from .lifecycle_manager import LifecycleManager, get_lifecycle_manager
from .service_registry import (
    ServiceConfig, ServiceState, DEFAULT_SERVICES, get_services_for_phase
)


class GPUManagerV2:
    """
    Production-ready GPU resource manager for MCN OS.

    Features:
    - Real-time VRAM monitoring
    - Automatic service lifecycle management
    - Pipeline-phase-aware scheduling
    - Priority-based preemption
    - Redis-based distributed locking
    """

    # RTX 4090 specs
    VRAM_TOTAL_MB = 24576
    VRAM_RESERVE_MB = 1024  # Reserve for system/desktop

    def __init__(
        self,
        redis_url: str = None,
        services: Dict[str, ServiceConfig] = None
    ):
        redis_url = redis_url or os.getenv(
            "REDIS_URL", "redis://:123456@localhost:6379/0"
        )
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.lock_key = "gpu_mutex_v2"
        self.default_timeout = 600  # 10 minutes for long workflows

        self.vram = get_vram_tracker()
        self.lifecycle = get_lifecycle_manager()
        self.services = services or DEFAULT_SERVICES

    # === VRAM Management ===

    def get_vram_status(self) -> VRAMStatus:
        """Get real-time VRAM status."""
        return self.vram.get_status()

    def get_available_vram(self) -> int:
        """Get available VRAM in MB (after reserve)."""
        status = self.get_vram_status()
        return max(0, status.free_mb - self.VRAM_RESERVE_MB)

    def can_start_service(self, service_name: str) -> bool:
        """Check if we have enough VRAM for a service."""
        config = self.services.get(service_name)
        if not config:
            return False
        return self.get_available_vram() >= config.vram_mb

    # === Pipeline Phase Management ===

    async def prepare_for_phase(self, phase: int) -> bool:
        """
        Prepare GPU for a specific pipeline phase.

        Automatically stops unnecessary services and starts required ones.

        Args:
            phase: Pipeline phase number
                   1 = Crawl (no GPU)
                   2 = Analysis (Vidi)
                   3 = Script/TTS (CosyVoice)
                   4 = Video Gen (ComfyUI)
                   5 = Render (no GPU)

        Returns:
            True if all required services are ready
        """
        logger.info(f"Preparing GPU for pipeline phase {phase}")

        # Find services needed for this phase
        needed = get_services_for_phase(phase)
        logger.debug(f"Services needed for phase {phase}: {needed}")

        # Find running services
        running = []
        for name in self.services:
            if await self.lifecycle.check_health(name):
                running.append(name)

        # Calculate VRAM needed
        needed_vram = sum(self.services[n].vram_mb for n in needed)
        logger.debug(f"VRAM needed: {needed_vram} MB, available: {self.get_available_vram()} MB")

        # Determine what to stop (not needed, lower priority)
        to_stop = [
            name for name in running
            if name not in needed
        ]

        # Sort by priority (stop lowest first)
        to_stop.sort(key=lambda n: self.services[n].priority)

        # Stop services until we have enough VRAM
        for service in to_stop:
            if self.get_available_vram() >= needed_vram:
                break
            logger.info(f"Stopping {service} to free VRAM for phase {phase}")
            await self.lifecycle.stop_service(service)
            await asyncio.sleep(2)  # Let VRAM be reclaimed

        # Start needed services
        success = True
        for service in needed:
            if not await self.lifecycle.check_health(service):
                logger.info(f"Starting {service} for phase {phase}")
                if not await self.lifecycle.ensure_service(service):
                    logger.error(f"Failed to start {service} for phase {phase}")
                    success = False

        return success

    async def release_all(self) -> None:
        """Stop all GPU services to free VRAM."""
        logger.info("Releasing all GPU services")
        for name in self.services:
            if await self.lifecycle.check_health(name):
                await self.lifecycle.stop_service(name)

    # === Service Locking ===

    @asynccontextmanager
    async def use_service(self, service_name: str, timeout: int = None):
        """
        Context manager for exclusive GPU service access.

        Ensures service is running, acquires lock, yields control,
        then releases lock (keeps service running for reuse).

        Args:
            service_name: Name of the service to use
            timeout: Lock timeout in seconds

        Yields:
            bool: True if service is ready, False on failure

        Usage:
            async with manager.use_service("comfyui") as ready:
                if ready:
                    result = execute_workflow(...)
        """
        timeout = timeout or self.default_timeout
        config = self.services.get(service_name)

        if not config:
            logger.error(f"Unknown service: {service_name}")
            yield False
            return

        # Preempt lower priority services if needed
        if not self.can_start_service(service_name):
            await self._preempt_for(service_name)

        # Ensure service is running
        if not await self.lifecycle.ensure_service(service_name):
            logger.error(f"Failed to start {service_name}")
            yield False
            return

        # Acquire Redis lock
        lock_acquired = self.redis.set(
            self.lock_key,
            service_name,
            nx=True,
            ex=timeout
        )

        if not lock_acquired:
            holder = self.redis.get(self.lock_key)
            logger.warning(f"GPU locked by {holder}, waiting...")

            # Wait for lock with exponential backoff
            for i in range(5):
                await asyncio.sleep(2 ** i)
                if self.redis.set(self.lock_key, service_name, nx=True, ex=timeout):
                    lock_acquired = True
                    break

        if not lock_acquired:
            logger.error(f"Could not acquire GPU lock for {service_name}")
            yield False
            return

        try:
            logger.info(f"GPU locked for {service_name}")
            yield True
        finally:
            # Release lock
            if self.redis.get(self.lock_key) == service_name:
                self.redis.delete(self.lock_key)
                logger.info(f"GPU lock released by {service_name}")

    async def _preempt_for(self, service_name: str) -> None:
        """Stop lower priority services to make room."""
        config = self.services[service_name]

        # Get running services sorted by priority (lowest first)
        running = []
        for name, svc in self.services.items():
            if name != service_name and await self.lifecycle.check_health(name):
                running.append((name, svc.priority, svc.vram_mb))

        running.sort(key=lambda x: x[1])  # Sort by priority

        # Stop services until we have enough VRAM
        for name, priority, vram in running:
            if priority >= config.priority:
                logger.warning(
                    f"Cannot preempt {name} (priority {priority}) "
                    f"for {service_name} (priority {config.priority})"
                )
                break

            if self.get_available_vram() >= config.vram_mb:
                break

            logger.info(f"Preempting {name} (priority {priority}) for {service_name}")
            await self.lifecycle.stop_service(name)
            await asyncio.sleep(2)

    # === Status & Monitoring ===

    async def get_status(self) -> Dict:
        """
        Get comprehensive GPU manager status.

        Returns:
            Dict with vram, services, and lock information
        """
        vram = self.get_vram_status()
        states = await self.lifecycle.get_all_states()

        return {
            "vram": {
                "total_mb": vram.total_mb,
                "used_mb": vram.used_mb,
                "free_mb": vram.free_mb,
                "available_mb": self.get_available_vram(),
                "processes": [
                    {"pid": p.pid, "name": p.name, "memory_mb": p.memory_mb}
                    for p in vram.processes
                ],
                "temperature_c": vram.temperature_c,
                "utilization_percent": vram.utilization_percent,
            },
            "services": {
                name: {
                    "state": state.value,
                    "vram_mb": self.services[name].vram_mb,
                    "priority": self.services[name].priority,
                    "phases": self.services[name].pipeline_phases,
                }
                for name, state in states.items()
            },
            "lock": {
                "holder": self.redis.get(self.lock_key),
                "ttl": self.redis.ttl(self.lock_key),
            }
        }

    def get_lock_holder(self) -> Optional[str]:
        """Get current GPU lock holder."""
        return self.redis.get(self.lock_key)

    def force_release_lock(self) -> bool:
        """Force release GPU lock (use with caution)."""
        return self.redis.delete(self.lock_key) > 0


# Singleton
_manager: Optional[GPUManagerV2] = None


def get_gpu_manager_v2() -> GPUManagerV2:
    """Get or create the singleton GPUManagerV2 instance."""
    global _manager
    if _manager is None:
        _manager = GPUManagerV2()
    return _manager
```

## Step 3.2: Verification Script

**File**: `middleware/scripts/test_gpu_manager_v2.py`

```python
#!/usr/bin/env python3
"""Test GPU Manager V2 functionality."""
import asyncio
import sys
sys.path.insert(0, '/mnt/data_ssd/mcn/middleware')

from lib.gpu_manager_v2 import get_gpu_manager_v2


async def main():
    print("=" * 60)
    print("GPU Manager V2 Test")
    print("=" * 60)

    manager = get_gpu_manager_v2()

    # Get full status
    status = await manager.get_status()

    print(f"\nVRAM Status:")
    vram = status["vram"]
    print(f"  Total:     {vram['total_mb']:,} MB")
    print(f"  Used:      {vram['used_mb']:,} MB")
    print(f"  Free:      {vram['free_mb']:,} MB")
    print(f"  Available: {vram['available_mb']:,} MB (after reserve)")
    print(f"  Temp:      {vram['temperature_c']}°C")

    print(f"\nGPU Processes:")
    for proc in vram["processes"]:
        print(f"  PID {proc['pid']}: {proc['memory_mb']:,} MB - {proc['name']}")

    print(f"\nServices:")
    for name, svc in status["services"].items():
        emoji = "🟢" if svc["state"] == "ready" else "🔴"
        phases = ",".join(str(p) for p in svc["phases"]) or "-"
        print(f"  {emoji} {name}: {svc['state']} | P{svc['priority']} | {svc['vram_mb']:,} MB | phases: {phases}")

    print(f"\nLock:")
    lock = status["lock"]
    print(f"  Holder: {lock['holder'] or 'None'}")
    print(f"  TTL:    {lock['ttl']}s")

    print("\n" + "=" * 60)
    print("Phase Preparation Commands:")
    print("  Phase 2 (Analysis): await manager.prepare_for_phase(2)")
    print("  Phase 3 (TTS):      await manager.prepare_for_phase(3)")
    print("  Phase 4 (Video):    await manager.prepare_for_phase(4)")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
```

## Verification Checklist

```bash
# 1. Run the test script
cd /mnt/data_ssd/mcn/middleware
source .venv/bin/activate
python scripts/test_gpu_manager_v2.py

# 2. Test phase preparation (interactive)
python -c "
import asyncio
from lib.gpu_manager_v2 import get_gpu_manager_v2

async def test():
    mgr = get_gpu_manager_v2()

    print('Current status:')
    status = await mgr.get_status()
    for name, svc in status['services'].items():
        print(f'  {name}: {svc[\"state\"]}')

    print('\nPreparing for Phase 4 (Video Generation)...')
    success = await mgr.prepare_for_phase(4)
    print(f'Result: {\"SUCCESS\" if success else \"FAILED\"}')

    print('\nNew status:')
    status = await mgr.get_status()
    for name, svc in status['services'].items():
        print(f'  {name}: {svc[\"state\"]}')

asyncio.run(test())
"

# 3. Verify ComfyUI is running
curl -s http://localhost:8188/system_stats | jq '.system.python_version'

# 4. Verify CosyVoice is NOT running (preempted)
curl -s http://localhost:50000/docs || echo "CosyVoice stopped (expected)"
```

## Success Criteria

- [ ] `get_status()` returns VRAM, services, and lock info
- [ ] `prepare_for_phase(4)` stops CosyVoice/Vidi and starts ComfyUI
- [ ] `prepare_for_phase(3)` stops ComfyUI and starts CosyVoice
- [ ] Redis lock is acquired/released correctly
- [ ] Preemption respects priority order

## Next Step

Once Phase 3 is verified, proceed to [06-PHASE4-WORKER-INTEGRATION.md](./06-PHASE4-WORKER-INTEGRATION.md).
