#!/usr/bin/env python3
"""Quick Vidi 4-bit test"""
import sys
sys.path.insert(0, '/home/jimmy/Documents/mcn/middleware')

from lib.vidi_client import VidiClient
import time

print("="*60)
print("VIDI 4-BIT QUANTIZATION TEST")
print("="*60)

# Initialize with 4-bit
print("\n1. Initializing VidiClient with 4-bit quantization...")
vidi = VidiClient(load_4bit=True)

print(f"   ✅ Model: {vidi.model_version}")
print(f"   ✅ Quantization: 4-bit")
print(f"   ✅ Expected VRAM: ~5GB (vs 18GB full precision)")

# Test video
video = "/mnt/data_ssd/mcn/visual/ComfyUI/output/video/LTX-2_00013_.mp4"
query = "person"

print(f"\n2. Running inference...")
print(f"   Video: {video}")
print(f"   Query: '{query}'")
print(f"   (This will take 30-120 seconds...)")

start = time.time()
try:
    timestamps = vidi.find_timestamps(video, query, timeout=180)
    elapsed = time.time() - start

    print(f"\n✅ SUCCESS!")
    print(f"   Time: {elapsed:.1f}s")
    print(f"   Found: {len(timestamps)} timestamp(s)")

    for i, ts in enumerate(timestamps, 1):
        print(f"   {i}. {ts['start']} - {ts['end']}")

except Exception as e:
    elapsed = time.time() - start
    print(f"\n❌ FAILED after {elapsed:.1f}s")
    print(f"   Error: {e}")
    sys.exit(1)

print("\n" + "="*60)
