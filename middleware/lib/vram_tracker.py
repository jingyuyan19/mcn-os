"""
VRAM Tracker - Real-time GPU memory monitoring via pynvml.

Usage:
    from lib.vram_tracker import get_vram_tracker

    tracker = get_vram_tracker()
    status = tracker.get_status()
    print(f"Free VRAM: {status.free_mb} MB")

    if tracker.can_fit(20000):
        print("Can start ComfyUI")
"""
from dataclasses import dataclass
from typing import List, Optional
from loguru import logger

# Try to import pynvml, but handle gracefully if not available (e.g., in Docker without GPU access)
try:
    import pynvml
    PYNVML_AVAILABLE = True
except ImportError:
    pynvml = None
    PYNVML_AVAILABLE = False
    logger.warning("pynvml not available - GPU monitoring disabled")


@dataclass
class GPUProcess:
    """A process using GPU memory."""
    pid: int
    name: str
    memory_mb: int


@dataclass
class VRAMStatus:
    """Current GPU memory status."""
    total_mb: int
    used_mb: int
    free_mb: int
    processes: List[GPUProcess]
    temperature_c: Optional[int] = None
    utilization_percent: Optional[int] = None


class VRAMTracker:
    """
    Track GPU VRAM usage in real-time using pynvml.

    Thread-safe singleton pattern recommended via get_vram_tracker().
    """

    def __init__(self, device_index: int = 0):
        self.device_index = device_index
        self._initialized = False
        self._handle = None

    def _ensure_init(self):
        """Lazy initialization of NVML."""
        if not self._initialized:
            if not PYNVML_AVAILABLE:
                logger.warning("NVML not available - using fallback mode")
                self._initialized = True
                self._handle = None
                return

            try:
                pynvml.nvmlInit()
                self._handle = pynvml.nvmlDeviceGetHandleByIndex(self.device_index)
                self._initialized = True
                logger.debug("NVML initialized successfully")
            except Exception as e:
                logger.warning(f"NVML initialization failed, using fallback: {e}")
                self._initialized = True
                self._handle = None

    def get_status(self) -> VRAMStatus:
        """
        Get current VRAM status.

        Returns:
            VRAMStatus with total, used, free memory and process list
        """
        self._ensure_init()

        # Fallback mode when NVML is not available
        if self._handle is None:
            return VRAMStatus(
                total_mb=24576,  # RTX 4090 default
                used_mb=0,
                free_mb=24576,
                processes=[],
                temperature_c=None,
                utilization_percent=None
            )

        # Memory info
        mem_info = pynvml.nvmlDeviceGetMemoryInfo(self._handle)
        total_mb = mem_info.total // (1024 * 1024)
        used_mb = mem_info.used // (1024 * 1024)
        free_mb = mem_info.free // (1024 * 1024)

        # Process info
        processes = []
        try:
            procs = pynvml.nvmlDeviceGetComputeRunningProcesses(self._handle)
            for p in procs:
                try:
                    name = pynvml.nvmlSystemGetProcessName(p.pid)
                    if isinstance(name, bytes):
                        name = name.decode('utf-8')
                except Exception:
                    name = f"pid_{p.pid}"

                processes.append(GPUProcess(
                    pid=p.pid,
                    name=name,
                    memory_mb=(p.usedGpuMemory or 0) // (1024 * 1024)
                ))
        except pynvml.NVMLError as e:
            logger.warning(f"Could not get GPU processes: {e}")

        # Temperature and utilization (optional)
        temp = None
        util_percent = None
        try:
            temp = pynvml.nvmlDeviceGetTemperature(
                self._handle, pynvml.NVML_TEMPERATURE_GPU
            )
            util = pynvml.nvmlDeviceGetUtilizationRates(self._handle)
            util_percent = util.gpu
        except pynvml.NVMLError:
            pass

        return VRAMStatus(
            total_mb=total_mb,
            used_mb=used_mb,
            free_mb=free_mb,
            processes=processes,
            temperature_c=temp,
            utilization_percent=util_percent
        )

    def can_fit(self, required_mb: int, safety_margin_mb: int = 1024) -> bool:
        """
        Check if required VRAM can fit with safety margin.

        Args:
            required_mb: Required VRAM in MB
            safety_margin_mb: Extra headroom (default 1GB for system)

        Returns:
            True if there's enough free VRAM
        """
        status = self.get_status()
        available = status.free_mb - safety_margin_mb
        can_fit = available >= required_mb

        logger.debug(
            f"VRAM check: need {required_mb} MB, "
            f"have {available} MB (free={status.free_mb}, margin={safety_margin_mb})"
        )
        return can_fit

    def get_process_by_name(self, name_pattern: str) -> Optional[GPUProcess]:
        """Find a GPU process by name pattern."""
        status = self.get_status()
        for proc in status.processes:
            if name_pattern.lower() in proc.name.lower():
                return proc
        return None

    def shutdown(self):
        """Clean up NVML resources."""
        if self._initialized:
            try:
                pynvml.nvmlShutdown()
                self._initialized = False
                logger.debug("NVML shutdown complete")
            except pynvml.NVMLError as e:
                logger.warning(f"NVML shutdown error: {e}")


# Singleton instance
_tracker: Optional[VRAMTracker] = None


def get_vram_tracker(device_index: int = 0) -> VRAMTracker:
    """
    Get or create the singleton VRAMTracker instance.

    Args:
        device_index: GPU device index (default 0)

    Returns:
        VRAMTracker instance
    """
    global _tracker
    if _tracker is None:
        _tracker = VRAMTracker(device_index)
    return _tracker
