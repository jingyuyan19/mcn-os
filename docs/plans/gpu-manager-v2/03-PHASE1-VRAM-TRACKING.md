# Phase 1: VRAM Tracking

**Risk Level**: Low
**Dependencies**: None
**Estimated Effort**: 1 day

## Overview

Create a VRAM tracking module using NVIDIA's pynvml library for real-time GPU memory monitoring.

## Prerequisites

```bash
# Verify NVIDIA driver is installed
nvidia-smi

# Should show RTX 4090 with 24GB
```

## Step 1.1: Add pynvml Dependency

**File**: `middleware/requirements.txt`

**Action**: Add the following line:
```
pynvml>=11.5.0
```

**Verification**:
```bash
# From Docker container
docker exec mcn_core pip install pynvml

# Or rebuild
docker-compose build mcn_core
```

## Step 1.2: Create VRAM Tracker Module

**File**: `middleware/lib/vram_tracker.py`

```python
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
import pynvml
from dataclasses import dataclass
from typing import List, Optional
from loguru import logger


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
            try:
                pynvml.nvmlInit()
                self._handle = pynvml.nvmlDeviceGetHandleByIndex(self.device_index)
                self._initialized = True
                logger.debug("NVML initialized successfully")
            except pynvml.NVMLError as e:
                logger.error(f"Failed to initialize NVML: {e}")
                raise

    def get_status(self) -> VRAMStatus:
        """
        Get current VRAM status.

        Returns:
            VRAMStatus with total, used, free memory and process list
        """
        self._ensure_init()

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
```

## Step 1.3: Verification Script

**File**: `middleware/scripts/test_vram_tracker.py`

```python
#!/usr/bin/env python3
"""Quick test for VRAM tracker."""
import sys
sys.path.insert(0, '/mnt/data_ssd/mcn/middleware')

from lib.vram_tracker import get_vram_tracker

def main():
    print("=" * 60)
    print("VRAM Tracker Test")
    print("=" * 60)

    tracker = get_vram_tracker()
    status = tracker.get_status()

    print(f"\nGPU Memory:")
    print(f"  Total:       {status.total_mb:,} MB")
    print(f"  Used:        {status.used_mb:,} MB")
    print(f"  Free:        {status.free_mb:,} MB")
    print(f"  Temperature: {status.temperature_c}°C")
    print(f"  Utilization: {status.utilization_percent}%")

    print(f"\nGPU Processes ({len(status.processes)}):")
    for proc in status.processes:
        print(f"  PID {proc.pid}: {proc.memory_mb:,} MB - {proc.name}")

    print(f"\nCan fit tests:")
    for size in [4000, 10000, 18000, 20000, 22000]:
        can_fit = tracker.can_fit(size)
        emoji = "✓" if can_fit else "✗"
        print(f"  {emoji} {size:,} MB: {'YES' if can_fit else 'NO'}")

    tracker.shutdown()
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
```

## Verification Checklist

Run these commands to verify Phase 1 is complete:

```bash
# 1. Check pynvml is installed
docker exec mcn_core python -c "import pynvml; print('pynvml OK')"

# 2. Run the test script (from host, since pynvml needs GPU access)
cd /mnt/data_ssd/mcn/middleware
source .venv/bin/activate
python scripts/test_vram_tracker.py

# Expected output:
# GPU Memory:
#   Total:       24,576 MB
#   Used:        X,XXX MB
#   Free:        XX,XXX MB
#   ...
```

## Success Criteria

- [ ] `pynvml` installed and importable
- [ ] `VRAMTracker.get_status()` returns valid data
- [ ] `VRAMTracker.can_fit()` correctly compares against free VRAM
- [ ] GPU processes listed with memory usage
- [ ] No errors when running test script

## Troubleshooting

### Error: "NVML Shared Library Not Found"
```bash
# Install NVIDIA driver utilities
sudo apt install nvidia-utils-535

# Or set library path
export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH
```

### Error: "Insufficient Permissions"
```bash
# Add user to video group
sudo usermod -a -G video $USER
# Log out and back in
```

### Error: "No GPU Found"
```bash
# Verify GPU is visible
nvidia-smi

# Check CUDA_VISIBLE_DEVICES
echo $CUDA_VISIBLE_DEVICES
```

## Next Step

Once Phase 1 is verified, proceed to [04-PHASE2-LIFECYCLE-MANAGER.md](./04-PHASE2-LIFECYCLE-MANAGER.md).
