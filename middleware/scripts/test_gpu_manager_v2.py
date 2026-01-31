#!/usr/bin/env python3
"""Test GPU Manager V2 functionality."""
import asyncio
import sys
sys.path.insert(0, '/mnt/data_ssd/mcn/middleware')

from lib.gpu_manager_v2 import get_gpu_manager_v2


async def main():
    print("=" * 60)
    print("GPU Manager V2 Test")
    print("=" * 60)

    manager = get_gpu_manager_v2()

    # Get full status
    status = await manager.get_status()

    print(f"\nVRAM Status:")
    vram = status["vram"]
    print(f"  Total:     {vram['total_mb']:,} MB")
    print(f"  Used:      {vram['used_mb']:,} MB")
    print(f"  Free:      {vram['free_mb']:,} MB")
    print(f"  Available: {vram['available_mb']:,} MB (after reserve)")
    print(f"  Temp:      {vram['temperature_c']}°C")

    print(f"\nGPU Processes:")
    for proc in vram["processes"]:
        print(f"  PID {proc['pid']}: {proc['memory_mb']:,} MB - {proc['name']}")

    print(f"\nServices:")
    for name, svc in status["services"].items():
        emoji = "🟢" if svc["state"] == "ready" else "🔴"
        phases = ",".join(str(p) for p in svc["phases"]) or "-"
        print(f"  {emoji} {name}: {svc['state']} | P{svc['priority']} | {svc['vram_mb']:,} MB | phases: {phases}")

    print(f"\nLock:")
    lock = status["lock"]
    print(f"  Holder: {lock['holder'] or 'None'}")
    print(f"  TTL:    {lock['ttl']}s")

    print("\n" + "=" * 60)
    print("Phase Preparation Commands:")
    print("  Phase 2 (Analysis): await manager.prepare_for_phase(2)")
    print("  Phase 3 (TTS):      await manager.prepare_for_phase(3)")
    print("  Phase 4 (Video):    await manager.prepare_for_phase(4)")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
