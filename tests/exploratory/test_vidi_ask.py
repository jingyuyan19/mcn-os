import sys
import os
import time
# Add parent dir to path so we can import middleware
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from middleware.lib.vidi_client import VidiClient

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 test_vidi_ask.py <video_path> [query]")
        print("Example: python3 test_vidi_ask.py video.mp4 'Describe the video.'")
        sys.exit(1)

    video_path = sys.argv[1]
    query = sys.argv[2] if len(sys.argv) > 2 else "Please describe the video detailedly."

    client = VidiClient()
    
    if not client.is_available():
        print("Error: Vidi model not available/installed.")
        # sys.exit(1) # Try anyway

    print(f"--- Vidi VQA Test ---")
    print(f"Video: {video_path}")
    print(f"Query: {query}")
    print("Sending request... (This may take a few minutes)")

    try:
        start_time = time.time()
        response = client.ask_vqa(video_path, query, timeout=600)
        end_time = time.time()
        
        print("\n=== Response ===")
        print(response)
        print("================")
        print(f"Time taken: {end_time - start_time:.2f} seconds")
        
    except Exception as e:
        print(f"\nError: {e}")

if __name__ == "__main__":
    main()
