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
