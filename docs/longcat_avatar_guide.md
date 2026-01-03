# 🎬 LongCat Avatar - RTX 4090 Best Practice Guide

## 📋 Quick Start

1. **Start ComfyUI** with optimized script: `./start_comfyui.sh`
2. **Load workflow**: `LongCatAvatar_4090_BestPractice.json`
3. **Select models in dropdowns** (first time only)
4. **Upload** portrait image + audio
5. **Queue Prompt!**

---

## ⚡ RTX 4090 Optimized Settings

| Setting | Value | Why |
|---------|-------|-----|
| **Resolution** | 720×720 | Trained resolution, stable |
| **Block Swap** | 0 | 24GB doesn't need offload |
| **Attention** | SDPA | Best for RTX 4090 |
| **Load Device** | main_device | Keep model on GPU |
| **Audio Duration** | 3600 sec | Up to 1 hour |

### ComfyUI Launch Flags
```bash
--highvram --use-pytorch-cross-attention --cuda-malloc --fast
```

---

## 📁 Model Selection

| Node | Select |
|------|--------|
| **WanVideoModelLoader** | `WanVideo/LongCat_bf16.safetensors` |
| **WanVideoVAELoader** | `Wan2_1_VAE_bf16.safetensors` |
| **WanVideoLoraSelect** | `LongCat_distill_lora_alpha64_bf16.safetensors` |
| **MelBandRoFormer** | `MelBandRoformer_fp32.safetensors` |
| **Wav2Vec2** | `chinese-wav2vec2-base` |
| **TextEncoder** | `umt5-xxl-enc-bf16.safetensors` |

---

## 🎥 Long Video (4+ Minutes)

LongCat uses **sliding window** architecture:
- Generates ~5 sec chunks → stitches with overlap
- **VRAM stays constant** regardless of total length!
- Workflow has **Extend groups** for auto-extending

### Key Parameters
- `context_overlap`: 14-16 frames (smooth transitions)
- `frame_count`: 93 (maximizes 5.8 sec context)

---

## 🖼️ Input Requirements

**Image:**
- Resolution: Any (auto-resized to 720×720)
- Format: Square portrait works best
- Content: Clear frontal face

**Audio:**
- Format: MP3/WAV
- Length: Up to 1 hour supported
- Quality: Clean speech (MelBandRoformer separates vocals)

---

## ⚠️ Troubleshooting

| Issue | Fix |
|-------|-----|
| OOM Error | Increase Block Swap to 10-15 |
| Black frames | Lower LoRA strength to 0.5 |
| Bad quality | Increase steps to 30-50, CFG to 5-6 |
| Slow generation | Use distill LoRA, 12-20 steps |
| Face distortion | Use trained resolution (720×720 or 1280×720) |

---

## 📊 Available Workflows

| Workflow | Resolution | Best For |
|----------|------------|----------|
| `LongCatAvatar_4090_BestPractice.json` | 720×720 | **Recommended** |
| `LongCatAvatar_4090_LongVideo.json` | 576×576 | If OOM issues |
| `LongCatAvatar_audio_image_to_video_example_01.json` | 832×480 | Original |
