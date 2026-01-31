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
