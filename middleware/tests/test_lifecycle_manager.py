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
