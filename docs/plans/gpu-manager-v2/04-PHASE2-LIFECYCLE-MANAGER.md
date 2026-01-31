# Phase 2: Lifecycle Manager

**Risk Level**: Medium
**Dependencies**: Phase 1 (VRAM Tracking)
**Estimated Effort**: 2 days

## Overview

Create service registry and lifecycle manager for Docker and native GPU services.

## Prerequisites

- Phase 1 complete (VRAM Tracker working)
- Docker SDK installed: `pip install docker>=6.0.0`
- httpx installed: `pip install httpx>=0.24.0`

## Step 2.1: Create Service Registry

**File**: `middleware/lib/service_registry.py`

```python
"""
Service Registry - Configuration for all GPU services.

Defines metadata for each GPU service including:
- Type (Docker or Native)
- VRAM requirements
- Priority for preemption
- Health check endpoints
- Start/stop commands
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict


class ServiceType(Enum):
    """Type of GPU service."""
    DOCKER = "docker"
    NATIVE = "native"


class ServiceState(Enum):
    """Current state of a service."""
    UNKNOWN = "unknown"
    STOPPED = "stopped"
    STARTING = "starting"
    READY = "ready"
    BUSY = "busy"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class ServiceConfig:
    """Configuration for a GPU service."""
    name: str
    type: ServiceType
    vram_mb: int
    priority: int  # Higher = more important, won't be preempted
    health_endpoint: str
    health_timeout: int = 60  # Seconds to wait for healthy
    warm_time: int = 10  # Seconds after start before checking health
    pipeline_phases: List[int] = field(default_factory=list)

    # Docker-specific
    container_name: Optional[str] = None

    # Native-specific
    start_cmd: Optional[str] = None
    stop_cmd: Optional[str] = None
    pid_file: Optional[str] = None

    # Special handling
    evict_api: Optional[str] = None  # API endpoint for graceful unload


# Default service registry for MCN OS
DEFAULT_SERVICES: Dict[str, ServiceConfig] = {
    "comfyui": ServiceConfig(
        name="comfyui",
        type=ServiceType.NATIVE,
        vram_mb=20000,  # 20 GB for LongCat
        priority=100,   # Highest priority
        health_endpoint="http://localhost:8188/system_stats",
        health_timeout=120,  # Slow to load models
        warm_time=30,
        pipeline_phases=[4],  # Video Generation
        start_cmd="/home/jimmy/Documents/mcn/start_comfy.sh",
        stop_cmd="pkill -f 'python.*main.py.*8188'",
        pid_file="/mnt/data_ssd/mcn/comfy.pid",
    ),
    "cosyvoice": ServiceConfig(
        name="cosyvoice",
        type=ServiceType.DOCKER,
        vram_mb=4000,
        priority=50,
        health_endpoint="http://localhost:50000/docs",
        health_timeout=60,
        warm_time=10,
        pipeline_phases=[3],  # TTS
        container_name="mcn_cosyvoice",
    ),
    "vidi": ServiceConfig(
        name="vidi",
        type=ServiceType.NATIVE,
        vram_mb=4000,
        priority=40,
        health_endpoint="http://localhost:8099/health",
        health_timeout=90,
        warm_time=20,
        pipeline_phases=[2],  # Analysis
        start_cmd="/home/jimmy/Documents/mcn/start_vidi.sh",
        stop_cmd="pkill -f 'vidi'",
        pid_file="/mnt/data_ssd/mcn/vidi.pid",
    ),
    "ollama": ServiceConfig(
        name="ollama",
        type=ServiceType.DOCKER,
        vram_mb=18000,  # qwen2.5:32b
        priority=10,    # Lowest - fallback only
        health_endpoint="http://localhost:11434/api/tags",
        health_timeout=30,
        warm_time=5,
        pipeline_phases=[],  # On-demand fallback
        container_name="mcn_ollama",
        evict_api="http://localhost:11434/api/generate",
    ),
}


def get_services_for_phase(phase: int) -> List[str]:
    """Get service names required for a pipeline phase."""
    return [
        name for name, config in DEFAULT_SERVICES.items()
        if phase in config.pipeline_phases
    ]


def get_service_config(name: str) -> Optional[ServiceConfig]:
    """Get configuration for a service by name."""
    return DEFAULT_SERVICES.get(name)
```

## Step 2.2: Create Lifecycle Manager

**File**: `middleware/lib/lifecycle_manager.py`

```python
"""
Lifecycle Manager - Start, stop, and monitor GPU services.

Handles both Docker containers and native processes with:
- Health check polling
- Graceful shutdown
- Warm-up time handling
"""
import asyncio
import subprocess
import time
from typing import Optional, Dict
import httpx
import docker
from loguru import logger

from .service_registry import (
    ServiceConfig, ServiceType, ServiceState, DEFAULT_SERVICES
)


class LifecycleManager:
    """
    Manages lifecycle of GPU services (Docker and native).

    Usage:
        manager = LifecycleManager()

        # Start a service
        await manager.ensure_service("comfyui")

        # Stop a service
        await manager.stop_service("cosyvoice")

        # Check health
        is_healthy = await manager.check_health("vidi")
    """

    def __init__(self, services: Dict[str, ServiceConfig] = None):
        self.services = services or DEFAULT_SERVICES
        self._states: Dict[str, ServiceState] = {}
        self._docker_client: Optional[docker.DockerClient] = None

    @property
    def docker(self) -> docker.DockerClient:
        """Lazy-load Docker client."""
        if self._docker_client is None:
            self._docker_client = docker.from_env()
        return self._docker_client

    # === Health Checks ===

    async def check_health(self, service_name: str) -> bool:
        """
        Check if service is healthy via HTTP endpoint.

        Args:
            service_name: Name of the service

        Returns:
            True if service responds with 200 OK
        """
        config = self.services.get(service_name)
        if not config:
            logger.warning(f"Unknown service: {service_name}")
            return False

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    config.health_endpoint,
                    timeout=10.0
                )
                healthy = resp.status_code == 200
                if healthy:
                    self._states[service_name] = ServiceState.READY
                return healthy
        except Exception as e:
            logger.debug(f"Health check failed for {service_name}: {e}")
            return False

    async def wait_for_health(
        self,
        service_name: str,
        timeout: Optional[int] = None
    ) -> bool:
        """
        Wait for service to become healthy.

        Args:
            service_name: Name of the service
            timeout: Max seconds to wait (default from config)

        Returns:
            True if service became healthy within timeout
        """
        config = self.services.get(service_name)
        if not config:
            return False

        timeout = timeout or config.health_timeout
        start = time.time()

        logger.info(f"Waiting for {service_name} to become healthy (timeout: {timeout}s)")

        while time.time() - start < timeout:
            if await self.check_health(service_name):
                elapsed = time.time() - start
                logger.info(f"Service {service_name} healthy after {elapsed:.1f}s")
                return True
            await asyncio.sleep(2)

        logger.error(f"Service {service_name} health check timed out after {timeout}s")
        self._states[service_name] = ServiceState.ERROR
        return False

    # === Docker Services ===

    def _get_container(self, container_name: str):
        """Get Docker container by name."""
        try:
            return self.docker.containers.get(container_name)
        except docker.errors.NotFound:
            logger.warning(f"Container not found: {container_name}")
            return None
        except docker.errors.APIError as e:
            logger.error(f"Docker API error: {e}")
            return None

    async def start_docker_service(self, service_name: str) -> bool:
        """
        Start a Docker-based GPU service.

        Args:
            service_name: Name of the service

        Returns:
            True if service started and healthy
        """
        config = self.services.get(service_name)
        if not config or config.type != ServiceType.DOCKER:
            logger.error(f"Not a Docker service: {service_name}")
            return False

        container = self._get_container(config.container_name)
        if not container:
            logger.error(f"Container {config.container_name} not found. Run docker-compose up -d")
            return False

        if container.status == "running":
            logger.info(f"Container {config.container_name} already running")
            return await self.check_health(service_name)

        logger.info(f"Starting container {config.container_name}")
        self._states[service_name] = ServiceState.STARTING

        try:
            container.start()
            logger.debug(f"Waiting {config.warm_time}s for warm-up")
            await asyncio.sleep(config.warm_time)

            if await self.wait_for_health(service_name):
                self._states[service_name] = ServiceState.READY
                return True
            else:
                self._states[service_name] = ServiceState.ERROR
                return False
        except Exception as e:
            logger.error(f"Failed to start {service_name}: {e}")
            self._states[service_name] = ServiceState.ERROR
            return False

    async def stop_docker_service(
        self,
        service_name: str,
        force: bool = False
    ) -> bool:
        """
        Stop a Docker-based GPU service.

        Args:
            service_name: Name of the service
            force: If True, kill instead of stop

        Returns:
            True if service stopped
        """
        config = self.services.get(service_name)
        if not config or config.type != ServiceType.DOCKER:
            return False

        # Special handling for Ollama: evict model first
        if config.evict_api:
            await self._evict_ollama_model(config.evict_api)

        container = self._get_container(config.container_name)
        if not container or container.status != "running":
            self._states[service_name] = ServiceState.STOPPED
            return True

        logger.info(f"Stopping container {config.container_name}")
        self._states[service_name] = ServiceState.STOPPING

        try:
            if force:
                container.kill()
            else:
                container.stop(timeout=30)

            self._states[service_name] = ServiceState.STOPPED
            logger.info(f"Container {config.container_name} stopped")
            await asyncio.sleep(2)  # Let VRAM be reclaimed
            return True
        except Exception as e:
            logger.error(f"Failed to stop {service_name}: {e}")
            return False

    async def _evict_ollama_model(self, evict_api: str):
        """Send keep_alive=0 to evict Ollama model from VRAM."""
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    evict_api,
                    json={"model": "qwen2.5:32b", "keep_alive": "0s"},
                    timeout=10.0
                )
                logger.info("Ollama model evicted from VRAM")
        except Exception as e:
            logger.debug(f"Ollama eviction skipped: {e}")

    # === Native Services ===

    async def start_native_service(self, service_name: str) -> bool:
        """
        Start a native (host) GPU service.

        Args:
            service_name: Name of the service

        Returns:
            True if service started and healthy
        """
        config = self.services.get(service_name)
        if not config or config.type != ServiceType.NATIVE:
            logger.error(f"Not a native service: {service_name}")
            return False

        # Check if already running
        if await self.check_health(service_name):
            logger.info(f"Service {service_name} already running")
            self._states[service_name] = ServiceState.READY
            return True

        logger.info(f"Starting native service {service_name}")
        self._states[service_name] = ServiceState.STARTING

        try:
            # Start in background
            process = subprocess.Popen(
                config.start_cmd,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )

            # Save PID if configured
            if config.pid_file:
                try:
                    with open(config.pid_file, 'w') as f:
                        f.write(str(process.pid))
                except Exception as e:
                    logger.warning(f"Could not write PID file: {e}")

            logger.debug(f"Waiting {config.warm_time}s for warm-up")
            await asyncio.sleep(config.warm_time)

            if await self.wait_for_health(service_name):
                self._states[service_name] = ServiceState.READY
                return True
            else:
                self._states[service_name] = ServiceState.ERROR
                return False
        except Exception as e:
            logger.error(f"Failed to start {service_name}: {e}")
            self._states[service_name] = ServiceState.ERROR
            return False

    async def stop_native_service(
        self,
        service_name: str,
        force: bool = False
    ) -> bool:
        """
        Stop a native GPU service.

        Args:
            service_name: Name of the service
            force: If True, use SIGKILL

        Returns:
            True if service stopped
        """
        config = self.services.get(service_name)
        if not config or config.type != ServiceType.NATIVE:
            return False

        logger.info(f"Stopping native service {service_name}")
        self._states[service_name] = ServiceState.STOPPING

        try:
            cmd = config.stop_cmd
            if force:
                cmd = cmd.replace("pkill", "pkill -9")

            subprocess.run(cmd, shell=True, timeout=30)
            self._states[service_name] = ServiceState.STOPPED
            logger.info(f"Service {service_name} stopped")
            await asyncio.sleep(3)  # Let VRAM be reclaimed
            return True
        except subprocess.TimeoutExpired:
            logger.warning(f"Stop command timed out for {service_name}")
            return False
        except Exception as e:
            logger.error(f"Failed to stop {service_name}: {e}")
            return False

    # === Unified Interface ===

    async def ensure_service(self, service_name: str) -> bool:
        """
        Ensure service is running and healthy.

        Args:
            service_name: Name of the service

        Returns:
            True if service is ready
        """
        config = self.services.get(service_name)
        if not config:
            logger.error(f"Unknown service: {service_name}")
            return False

        if config.type == ServiceType.DOCKER:
            return await self.start_docker_service(service_name)
        else:
            return await self.start_native_service(service_name)

    async def stop_service(
        self,
        service_name: str,
        force: bool = False
    ) -> bool:
        """
        Stop a service regardless of type.

        Args:
            service_name: Name of the service
            force: If True, force kill

        Returns:
            True if service stopped
        """
        config = self.services.get(service_name)
        if not config:
            return False

        if config.type == ServiceType.DOCKER:
            return await self.stop_docker_service(service_name, force)
        else:
            return await self.stop_native_service(service_name, force)

    def get_state(self, service_name: str) -> ServiceState:
        """Get cached service state."""
        return self._states.get(service_name, ServiceState.UNKNOWN)

    async def get_all_states(self) -> Dict[str, ServiceState]:
        """Get states of all services (with health checks)."""
        states = {}
        for name in self.services:
            if await self.check_health(name):
                states[name] = ServiceState.READY
            elif self._states.get(name) == ServiceState.STARTING:
                states[name] = ServiceState.STARTING
            else:
                states[name] = ServiceState.STOPPED
        return states


# Singleton
_manager: Optional[LifecycleManager] = None


def get_lifecycle_manager() -> LifecycleManager:
    """Get or create singleton LifecycleManager."""
    global _manager
    if _manager is None:
        _manager = LifecycleManager()
    return _manager
```

## Step 2.3: Verification Script

**File**: `middleware/scripts/test_lifecycle_manager.py`

```python
#!/usr/bin/env python3
"""Test lifecycle manager functionality."""
import asyncio
import sys
sys.path.insert(0, '/mnt/data_ssd/mcn/middleware')

from lib.lifecycle_manager import get_lifecycle_manager
from lib.service_registry import DEFAULT_SERVICES


async def main():
    print("=" * 60)
    print("Lifecycle Manager Test")
    print("=" * 60)

    manager = get_lifecycle_manager()

    # Check all service health
    print("\nService Health Check:")
    states = await manager.get_all_states()
    for name, state in states.items():
        config = DEFAULT_SERVICES[name]
        emoji = "🟢" if state.value == "ready" else "🔴"
        print(f"  {emoji} {name}: {state.value} (priority: {config.priority}, vram: {config.vram_mb} MB)")

    print("\n" + "=" * 60)
    print("Available Commands:")
    print("  python -c \"import asyncio; from lib.lifecycle_manager import get_lifecycle_manager; asyncio.run(get_lifecycle_manager().ensure_service('cosyvoice'))\"")
    print("  python -c \"import asyncio; from lib.lifecycle_manager import get_lifecycle_manager; asyncio.run(get_lifecycle_manager().stop_service('cosyvoice'))\"")


if __name__ == "__main__":
    asyncio.run(main())
```

## Verification Checklist

```bash
# 1. Check dependencies
docker exec mcn_core pip install docker httpx

# 2. Run the test script
cd /mnt/data_ssd/mcn/middleware
source .venv/bin/activate
python scripts/test_lifecycle_manager.py

# 3. Test Docker service control (CosyVoice)
python -c "
import asyncio
from lib.lifecycle_manager import get_lifecycle_manager

async def test():
    mgr = get_lifecycle_manager()
    print('Stopping CosyVoice...')
    await mgr.stop_service('cosyvoice')
    print('Starting CosyVoice...')
    await mgr.ensure_service('cosyvoice')
    print('Done!')

asyncio.run(test())
"

# 4. Verify VRAM changes
nvidia-smi
```

## Success Criteria

- [ ] `docker` and `httpx` installed
- [ ] Service registry loads all 4 services
- [ ] Health checks work for running services
- [ ] Docker services can be stopped/started
- [ ] Native services can be stopped/started
- [ ] VRAM is released after stopping a service

## Next Step

Once Phase 2 is verified, proceed to [05-PHASE3-GPU-MANAGER-V2.md](./05-PHASE3-GPU-MANAGER-V2.md).
