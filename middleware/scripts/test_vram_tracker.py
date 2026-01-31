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
