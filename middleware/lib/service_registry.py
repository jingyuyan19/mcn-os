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
