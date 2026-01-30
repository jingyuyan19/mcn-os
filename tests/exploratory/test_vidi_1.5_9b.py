#!/usr/bin/env python3
"""
Test script for Vidi 1.5 9B upgrade.

Tests all modes:
1. Retrieval - Find timestamps for text queries
2. VQA - Video question answering
3. Highlight - Auto-extract highlights (NEW in 1.5)
4. Grounding - Object detection with bounding boxes (NEW in 1.5)
"""
import sys
import os
sys.path.insert(0, '/home/jimmy/Documents/mcn/middleware')

from lib.vidi_client import VidiClient
import json

def test_vidi_upgrade():
    """Test Vidi 1.5 9B upgrade."""
    print("=" * 60)
    print("Vidi 1.5 9B Upgrade Test")
    print("=" * 60)

    # Initialize client
    client = VidiClient(use_9b=True)
    print(f"\n✓ Model version: {client.model_version}")
    print(f"✓ Model path: {client.model_path}")
    print(f"✓ Vidi directory: {client.vidi_dir}")
    print(f"✓ Available: {client.is_available()}")

    if not client.is_available():
        print("\n❌ Vidi is not available. Check installation.")
        return False

    # Test video path (use existing test video)
    test_video = "/home/jimmy/Documents/mcn/test_output/test_video.mp4"

    if not os.path.exists(test_video):
        print(f"\n⚠️  Test video not found: {test_video}")
        print("Please provide a test video path to continue.")
        return False

    print(f"\n✓ Test video: {test_video}")

    # Test 1: Retrieval mode
    print("\n" + "=" * 60)
    print("Test 1: Retrieval Mode (Find timestamps)")
    print("=" * 60)
    try:
        query = "person talking"
        print(f"Query: '{query}'")
        timestamps = client.find_timestamps(test_video, query, timeout=300)
        print(f"✓ Found {len(timestamps)} segments:")
        for i, ts in enumerate(timestamps):
            print(f"  {i+1}. {ts['start']} - {ts['end']}")
    except Exception as e:
        print(f"❌ Retrieval test failed: {e}")

    # Test 2: VQA mode
    print("\n" + "=" * 60)
    print("Test 2: VQA Mode (Video Question Answering)")
    print("=" * 60)
    try:
        query = "What is happening in this video?"
        print(f"Query: '{query}'")
        answer = client.ask_vqa(test_video, query, timeout=300)
        print(f"✓ Answer: {answer}")
    except Exception as e:
        print(f"❌ VQA test failed: {e}")

    # Test 3: Highlight mode (NEW in 1.5)
    print("\n" + "=" * 60)
    print("Test 3: Highlight Mode (Auto-extract highlights) - NEW")
    print("=" * 60)
    try:
        highlights = client.extract_highlights(test_video, timeout=300)
        print(f"✓ Found {len(highlights)} highlights:")
        for i, hl in enumerate(highlights):
            print(f"  {i+1}. {hl.get('start')} - {hl.get('end')}: {hl.get('title', 'N/A')}")
    except NotImplementedError as e:
        print(f"⚠️  {e}")
    except Exception as e:
        print(f"❌ Highlight test failed: {e}")

    # Test 4: Grounding mode (NEW in 1.5)
    print("\n" + "=" * 60)
    print("Test 4: Grounding Mode (Object detection) - NEW")
    print("=" * 60)
    try:
        query = "person"
        print(f"Query: '{query}'")
        objects = client.ground_objects(test_video, query, timeout=300)
        print(f"✓ Found {len(objects)} objects:")
        for i, obj in enumerate(objects):
            print(f"  {i+1}. {obj}")
    except NotImplementedError as e:
        print(f"⚠️  {e}")
    except Exception as e:
        print(f"❌ Grounding test failed: {e}")

    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Test Vidi 1.5 9B upgrade")
    parser.add_argument("--video", type=str, help="Path to test video")
    args = parser.parse_args()

    if args.video:
        # Override test video path
        import sys
        sys.modules[__name__].test_video = args.video

    test_vidi_upgrade()
