import sys
import os
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from middleware.lib.vidi_client import VidiClient

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 test_vidi_prompts.py <video_path>")
        sys.exit(1)

    video_path = sys.argv[1]
    client = VidiClient()

    if not client.is_available():
        print("Vidi not available.")
        sys.exit(1)

    # Prompts to test
    prompts = [
        "",  # Empty prompt (Implicit highlight?)
        "Highlight",
        "Highlight.",
        "Generate highlights.",
        "Describe this video.",
        "What is happening in this video?",
        "Please summarize the video events.",
    ]

    print(f"Testing {len(prompts)} prompts on: {video_path}")
    
    for i, p in enumerate(prompts):
        print(f"\n[{i+1}/{len(prompts)}] Testing prompt: '{p}'")
        try:
            start = time.time()
            # Use 'vqa' task which sends raw prompt
            # Note: client.ask_vqa calls _run_inference(..., task='vqa')
            # which in inference.py adds image token + prompt.
            response = client.ask_vqa(video_path, p, timeout=200)
            dur = time.time() - start
            
            print(f"Duration: {dur:.2f}s")
            if not response:
                print("Result: [EMPTY]")
            else:
                print(f"Result: {response}")
                
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
