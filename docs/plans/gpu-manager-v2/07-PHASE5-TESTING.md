# Phase 5: Testing

**Risk Level**: Low
**Dependencies**: All previous phases
**Estimated Effort**: 1 day

## Overview

Create comprehensive tests for GPU Manager V2 components.

## Test Structure

```
middleware/tests/
├── test_vram_tracker.py       # Unit tests for VRAM tracking
├── test_lifecycle_manager.py  # Unit tests for service lifecycle
├── test_gpu_manager_v2.py     # Integration tests
└── test_gpu_api.py            # API endpoint tests
```

## Step 5.1: VRAM Tracker Tests

**File**: `middleware/tests/test_vram_tracker.py`

```python
"""Unit tests for VRAM Tracker."""
import pytest
from unittest.mock import Mock, patch, MagicMock


class TestVRAMTracker:
    """Test VRAM tracking functionality."""

    @pytest.fixture
    def mock_pynvml(self):
        """Mock pynvml module."""
        with patch('lib.vram_tracker.pynvml') as mock:
            # Setup mock device handle
            mock_handle = Mock()
            mock.nvmlDeviceGetHandleByIndex.return_value = mock_handle

            # Setup mock memory info (24GB GPU, 4GB used)
            mem_info = Mock()
            mem_info.total = 24 * 1024 * 1024 * 1024  # 24 GB
            mem_info.used = 4 * 1024 * 1024 * 1024    # 4 GB
            mem_info.free = 20 * 1024 * 1024 * 1024   # 20 GB
            mock.nvmlDeviceGetMemoryInfo.return_value = mem_info

            # Setup mock processes
            mock_proc = Mock()
            mock_proc.pid = 12345
            mock_proc.usedGpuMemory = 2 * 1024 * 1024 * 1024  # 2 GB
            mock.nvmlDeviceGetComputeRunningProcesses.return_value = [mock_proc]
            mock.nvmlSystemGetProcessName.return_value = b"/usr/bin/python3"

            # Setup mock temperature
            mock.NVML_TEMPERATURE_GPU = 0
            mock.nvmlDeviceGetTemperature.return_value = 45

            # Setup mock utilization
            util = Mock()
            util.gpu = 25
            mock.nvmlDeviceGetUtilizationRates.return_value = util

            yield mock

    def test_get_status_returns_valid_data(self, mock_pynvml):
        """Test that get_status returns correct VRAM info."""
        from lib.vram_tracker import VRAMTracker

        tracker = VRAMTracker()
        status = tracker.get_status()

        assert status.total_mb == 24576
        assert status.used_mb == 4096
        assert status.free_mb == 20480
        assert status.temperature_c == 45
        assert status.utilization_percent == 25

    def test_get_status_includes_processes(self, mock_pynvml):
        """Test that processes are listed."""
        from lib.vram_tracker import VRAMTracker

        tracker = VRAMTracker()
        status = tracker.get_status()

        assert len(status.processes) == 1
        assert status.processes[0].pid == 12345
        assert status.processes[0].memory_mb == 2048

    def test_can_fit_returns_true_when_enough_vram(self, mock_pynvml):
        """Test can_fit with sufficient VRAM."""
        from lib.vram_tracker import VRAMTracker

        tracker = VRAMTracker()

        assert tracker.can_fit(18000) is True  # 18 GB fits in 20 GB free
        assert tracker.can_fit(19000) is True  # Just fits with 1GB margin

    def test_can_fit_returns_false_when_insufficient(self, mock_pynvml):
        """Test can_fit with insufficient VRAM."""
        from lib.vram_tracker import VRAMTracker

        tracker = VRAMTracker()

        assert tracker.can_fit(20000) is False  # Won't fit with 1GB margin
        assert tracker.can_fit(25000) is False  # Way too big

    def test_can_fit_respects_safety_margin(self, mock_pynvml):
        """Test that safety margin is applied."""
        from lib.vram_tracker import VRAMTracker

        tracker = VRAMTracker()

        # With 20GB free and 2GB margin, can fit 18GB
        assert tracker.can_fit(18000, safety_margin_mb=2048) is True
        assert tracker.can_fit(18500, safety_margin_mb=2048) is False
```

## Step 5.2: Lifecycle Manager Tests

**File**: `middleware/tests/test_lifecycle_manager.py`

```python
"""Unit tests for Lifecycle Manager."""
import pytest
from unittest.mock import Mock, patch, AsyncMock
import asyncio


class TestLifecycleManager:
    """Test service lifecycle management."""

    @pytest.fixture
    def manager(self):
        """Create lifecycle manager with mocked dependencies."""
        with patch('lib.lifecycle_manager.docker'):
            from lib.lifecycle_manager import LifecycleManager
            return LifecycleManager()

    @pytest.mark.asyncio
    async def test_check_health_success(self, manager):
        """Test successful health check."""
        with patch('lib.lifecycle_manager.httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200

            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value = mock_instance

            result = await manager.check_health("comfyui")
            assert result is True

    @pytest.mark.asyncio
    async def test_check_health_failure(self, manager):
        """Test failed health check."""
        with patch('lib.lifecycle_manager.httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(side_effect=Exception("Connection refused"))
            mock_client.return_value.__aenter__.return_value = mock_instance

            result = await manager.check_health("comfyui")
            assert result is False

    @pytest.mark.asyncio
    async def test_start_docker_service(self, manager):
        """Test Docker container start."""
        # Mock container
        mock_container = Mock()
        mock_container.status = "exited"

        # Mock Docker client
        manager._docker_client = Mock()
        manager._docker_client.containers.get.return_value = mock_container

        # Mock health check
        with patch.object(manager, 'wait_for_health', return_value=True):
            result = await manager.start_docker_service("cosyvoice")

            mock_container.start.assert_called_once()
            assert result is True

    @pytest.mark.asyncio
    async def test_start_docker_already_running(self, manager):
        """Test that already running container is not restarted."""
        mock_container = Mock()
        mock_container.status = "running"

        manager._docker_client = Mock()
        manager._docker_client.containers.get.return_value = mock_container

        with patch.object(manager, 'check_health', return_value=True):
            result = await manager.start_docker_service("cosyvoice")

            mock_container.start.assert_not_called()
            assert result is True

    @pytest.mark.asyncio
    async def test_stop_docker_service(self, manager):
        """Test Docker container stop."""
        mock_container = Mock()
        mock_container.status = "running"

        manager._docker_client = Mock()
        manager._docker_client.containers.get.return_value = mock_container

        result = await manager.stop_docker_service("cosyvoice")

        mock_container.stop.assert_called_once()
        assert result is True

    @pytest.mark.asyncio
    async def test_get_all_states(self, manager):
        """Test getting all service states."""
        async def mock_health(name):
            return name == "comfyui"

        with patch.object(manager, 'check_health', side_effect=mock_health):
            states = await manager.get_all_states()

            assert states["comfyui"].value == "ready"
            assert states["cosyvoice"].value == "stopped"
```

## Step 5.3: GPU Manager V2 Integration Tests

**File**: `middleware/tests/test_gpu_manager_v2.py`

```python
"""Integration tests for GPU Manager V2."""
import pytest
from unittest.mock import Mock, patch, AsyncMock


class TestGPUManagerV2:
    """Test GPU Manager V2 integration."""

    @pytest.fixture
    def manager(self):
        """Create GPU manager with mocked dependencies."""
        with patch('lib.gpu_manager_v2.redis') as mock_redis:
            with patch('lib.gpu_manager_v2.get_vram_tracker') as mock_vram:
                with patch('lib.gpu_manager_v2.get_lifecycle_manager') as mock_lifecycle:
                    # Setup VRAM mock
                    vram_tracker = Mock()
                    vram_status = Mock()
                    vram_status.total_mb = 24576
                    vram_status.used_mb = 4000
                    vram_status.free_mb = 20576
                    vram_status.processes = []
                    vram_status.temperature_c = 45
                    vram_status.utilization_percent = 10
                    vram_tracker.get_status.return_value = vram_status
                    mock_vram.return_value = vram_tracker

                    # Setup lifecycle mock
                    lifecycle = AsyncMock()
                    lifecycle.check_health = AsyncMock(return_value=False)
                    lifecycle.ensure_service = AsyncMock(return_value=True)
                    lifecycle.stop_service = AsyncMock(return_value=True)
                    lifecycle.get_all_states = AsyncMock(return_value={})
                    mock_lifecycle.return_value = lifecycle

                    # Setup Redis mock
                    redis_client = Mock()
                    redis_client.set.return_value = True
                    redis_client.get.return_value = None
                    redis_client.delete.return_value = 1
                    redis_client.ttl.return_value = -2
                    mock_redis.from_url.return_value = redis_client

                    from lib.gpu_manager_v2 import GPUManagerV2
                    mgr = GPUManagerV2()
                    mgr.lifecycle = lifecycle
                    mgr.vram = vram_tracker

                    yield mgr

    def test_get_available_vram(self, manager):
        """Test available VRAM calculation."""
        available = manager.get_available_vram()
        # 20576 free - 1024 reserve = 19552
        assert available == 19552

    def test_can_start_service_true(self, manager):
        """Test can_start_service when enough VRAM."""
        assert manager.can_start_service("vidi") is True  # 4000 MB
        assert manager.can_start_service("cosyvoice") is True  # 4000 MB

    def test_can_start_service_false(self, manager):
        """Test can_start_service when insufficient VRAM."""
        # Need 20000 MB but only have 19552 available
        assert manager.can_start_service("comfyui") is False

    @pytest.mark.asyncio
    async def test_prepare_for_phase_starts_service(self, manager):
        """Test that prepare_for_phase starts required services."""
        await manager.prepare_for_phase(2)  # Analysis phase needs Vidi

        manager.lifecycle.ensure_service.assert_called_with("vidi")

    @pytest.mark.asyncio
    async def test_prepare_for_phase_stops_unnecessary(self, manager):
        """Test that prepare_for_phase stops unnecessary services."""
        # Simulate cosyvoice running
        async def check_health(name):
            return name == "cosyvoice"
        manager.lifecycle.check_health = AsyncMock(side_effect=check_health)

        # Prepare for phase 4 (ComfyUI)
        await manager.prepare_for_phase(4)

        # Should stop cosyvoice
        manager.lifecycle.stop_service.assert_called_with("cosyvoice")

    @pytest.mark.asyncio
    async def test_use_service_acquires_lock(self, manager):
        """Test that use_service acquires Redis lock."""
        async with manager.use_service("vidi") as ready:
            assert ready is True
            manager.redis.set.assert_called()

    @pytest.mark.asyncio
    async def test_use_service_releases_lock(self, manager):
        """Test that use_service releases lock on exit."""
        manager.redis.get.return_value = "vidi"

        async with manager.use_service("vidi"):
            pass

        manager.redis.delete.assert_called_with("gpu_mutex_v2")

    @pytest.mark.asyncio
    async def test_get_status(self, manager):
        """Test get_status returns complete info."""
        manager.lifecycle.get_all_states = AsyncMock(return_value={
            "comfyui": Mock(value="stopped"),
            "cosyvoice": Mock(value="ready"),
        })

        status = await manager.get_status()

        assert "vram" in status
        assert "services" in status
        assert "lock" in status
        assert status["vram"]["total_mb"] == 24576
```

## Step 5.4: Run Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run all GPU Manager tests
cd /mnt/data_ssd/mcn/middleware
pytest tests/test_vram_tracker.py tests/test_lifecycle_manager.py tests/test_gpu_manager_v2.py -v

# Run with coverage
pytest tests/test_gpu_manager_v2.py --cov=lib --cov-report=term-missing

# Run specific test
pytest tests/test_gpu_manager_v2.py::TestGPUManagerV2::test_prepare_for_phase_starts_service -v
```

## Verification Checklist

```bash
# 1. All unit tests pass
pytest tests/test_vram_tracker.py -v
# Expected: All tests PASSED

# 2. All lifecycle tests pass
pytest tests/test_lifecycle_manager.py -v
# Expected: All tests PASSED

# 3. All integration tests pass
pytest tests/test_gpu_manager_v2.py -v
# Expected: All tests PASSED

# 4. Coverage meets target
pytest tests/ --cov=lib --cov-report=term-missing | grep "gpu_manager_v2"
# Expected: 80%+ coverage
```

## Success Criteria

- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] 80%+ code coverage for new modules
- [ ] No regressions in existing tests

## Next Step

Once Phase 5 is verified, proceed to [08-VERIFICATION-CHECKLIST.md](./08-VERIFICATION-CHECKLIST.md) for final system verification.
