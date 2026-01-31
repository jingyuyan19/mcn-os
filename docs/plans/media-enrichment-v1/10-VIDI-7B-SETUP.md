# Vidi 7B - Video Understanding Model Setup

**Status:** ✅ Operational (2026-01-31)
**VRAM Usage:** ~6.5 GB (4-bit quantization)
**Port:** 8099

## Overview

Vidi 7B provides video understanding capabilities for the media enrichment pipeline:
- **Temporal Grounding:** Find timestamps matching text queries
- **Video Q&A:** Answer questions about video content
- **Clip Extraction:** Extract video segments based on timestamps

## Quick Reference

```bash
# Start Vidi
./start_vidi.sh

# Health check
curl http://localhost:8099/health

# Find timestamps
curl -X POST http://localhost:8099/inference \
  -F "video=@/path/to/video.mp4" \
  -F "question=Find timestamps where a cat appears" \
  -F "task=retrieval"
```

## Integration with Media Enrichment Pipeline

```
Phase 2: Media Processing
    │
    ├── Video Analysis
    │   └── Vidi 7B (temporal grounding)
    │       ├── Find relevant clips
    │       ├── Extract B-roll segments
    │       └── Answer content questions
    │
    └── Output: Timestamped clips for Phase 4
```

### Python Client Usage

```python
from middleware.lib.vidi_client import VidiClient

client = VidiClient()

# Find B-roll timestamps
timestamps = client.find_timestamps(
    video_path="/path/to/source.mp4",
    query="person walking in city"
)
# Returns: [(10.5, 15.2), (45.0, 52.3)]

# Extract clips
clips = client.extract_clips(
    video_path="/path/to/source.mp4",
    timestamps=timestamps,
    output_dir="/output/broll/"
)
```

## Service Configuration

| Setting | Value |
|---------|-------|
| Host | localhost (runs on host, not Docker) |
| Port | 8099 |
| Quantization | 4-bit (via bitsandbytes) |
| VRAM | ~6.5 GB |
| Model Path | `/mnt/data_ssd/models/Vidi/Vidi-7B` |
| Startup | Auto via `start_mcn_os.sh` |

## Troubleshooting

### Dependencies Broken
```bash
cd /mnt/data_ssd/mcn/external/Vidi/Vidi_7B
source vidi7b_env/bin/activate
pip install -r requirements-frozen.txt
```

### CUDA OOM
Check GPU usage and kill competing processes:
```bash
nvidia-smi --query-compute-apps=pid,used_memory,name --format=csv
```

### Server Not Starting
Check logs:
```bash
tail -50 /mnt/data_ssd/mcn/external/Vidi/Vidi_7B/vidi_server.log
```

## Key Dependencies (Frozen)

| Package | Version | Notes |
|---------|---------|-------|
| torch | 2.4.0+cu121 | Must match flash-attn |
| flash-attn | 2.8.3+cu12torch2.4 | Prebuilt wheel |
| accelerate | 0.33.0 | Higher versions break 4-bit |
| bitsandbytes | 0.49.1 | For quantization |

## Files

```
/mnt/data_ssd/mcn/
├── start_vidi.sh                    # Startup script
├── external/Vidi/Vidi_7B/
│   ├── vidi_server.py               # FastAPI server
│   ├── vidi_server.log              # Logs
│   ├── vidi7b_env/                  # Python venv
│   ├── requirements-frozen.txt      # Frozen deps (67 packages)
│   └── README.md                    # Full documentation
└── middleware/lib/vidi_client.py    # Python client
```

## Verified Working (2026-01-31)

| Test | Query | Result |
|------|-------|--------|
| Temporal Grounding | "golden lock" | 00:00-00:29 ✅ |
| Temporal Grounding | "clock" | 00:28-00:42 ✅ |

## Related Docs

- [09-VLM-SELECTION.md](./09-VLM-SELECTION.md) - VLM comparison and selection
- [Full README](/mnt/data_ssd/mcn/external/Vidi/Vidi_7B/README.md) - Detailed setup guide
