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
