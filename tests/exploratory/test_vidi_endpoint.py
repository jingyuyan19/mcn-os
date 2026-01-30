import requests
import sys
import os

# Configuration
API_URL = "http://localhost:8000/video/search"
STATUS_URL = "http://localhost:8000/video/status"

def test_vidi(video_path, query="interesting moment"):
    """Test Vidi2 video search endpoint."""
    
    # 1. Check if video exists
    if not os.path.exists(video_path):
        print(f"❌ Error: Video file not found at {video_path}")
        return

    # 2. Check server status
    print("Checking server status...")
    try:
        resp = requests.get(STATUS_URL)
        if resp.status_code == 200:
            status = resp.json()
            print(f"✅ Server Ready: Vidi Available = {status.get('available')}")
            print(f"   Model Path: {status.get('model_path')}")
        else:
            print(f"❌ Server Error: {resp.status_code}")
            return
    except requests.exceptions.ConnectionError:
        print("❌ Error: Middleware server is not running on port 8000")
        print("   Run: ./start_mcn_os.sh or 'python3 middleware/server.py'")
        return

    # 3. Send search request
    print(f"\nSearching video: {os.path.basename(video_path)}")
    print(f"Query: '{query}'")
    print("Sending request (this takes ~10-30s)...")
    
    try:
        resp = requests.post(API_URL, json={
            "video_path": video_path,
            "query": query
        })
        
        if resp.status_code == 200:
            data = resp.json()
            timestamps = data.get("timestamps", [])
            print("\n✅ Search Successful!")
            print(f"Found {len(timestamps)} segments:")
            if timestamps:
                for ts in timestamps:
                    print(f"  - {ts['start']} to {ts['end']}")
            else:
                print("  (No matches found for this query)")
        else:
            print(f"\n❌ Request Failed: {resp.status_code}")
            print(f"Error: {resp.text}")
            
    except Exception as e:
        print(f"\n❌ Error during request: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 test_vidi_endpoint.py <video_path> [query]")
        print("Example: python3 test_vidi_endpoint.py /path/to/video.mp4 'funny scene'")
    else:
        vid_path = sys.argv[1]
        query = sys.argv[2] if len(sys.argv) > 2 else "interesting moment"
        test_vidi(vid_path, query)
