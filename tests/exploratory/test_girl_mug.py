#!/usr/bin/env python3
"""Test Vidi 7B 4-bit: Find girl holding a mug in Nvidia CES video"""
import sys
sys.path.insert(0, '/home/jimmy/Documents/mcn/middleware')

from lib.vidi_client import VidiClient
import time

print("="*60)
print("VIDI 7B (4-BIT) - GIRL HOLDING MUG TEST")
print("="*60)

vidi = VidiClient(load_4bit=True)
print(f"✅ Model: {vidi.model_version}")
print(f"✅ Quantization: 4-bit (~4GB VRAM)")

video = "/home/jimmy/Downloads/Nvidia's CES Keynote： Everything Announced in 9 Minutes - CNET (1080p, h264).mp4"
query = "girl holding a mug"

print(f"\n🎥 Video: Nvidia's CES Keynote")
print(f"🔍 Query: '{query}'")
print(f"⏳ Searching... (this may take 30-120 seconds)\n")

start = time.time()
try:
    timestamps = vidi.find_timestamps(video, query, timeout=300)
    elapsed = time.time() - start

    print(f"✅ FOUND {len(timestamps)} TIMESTAMP(S) in {elapsed:.1f}s\n")

    if timestamps:
        for i, ts in enumerate(timestamps, 1):
            print(f"  {i}. {ts['start']} - {ts['end']}")
    else:
        print("  No matches found.")

except Exception as e:
    elapsed = time.time() - start
    print(f"❌ FAILED after {elapsed:.1f}s")
    print(f"   Error: {e}")

print("\n" + "="*60)
