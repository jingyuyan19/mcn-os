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
