# MCN OS Current State

**Last Updated:** 2026-01-07  
**Version:** 1.1 (Phase 10 In Progress)

---

## ✅ What's Working

### Full Pipeline Verified
```
n8n Trigger → Sanity → DeepSeek Brain → Middleware → Remotion → MP4
```

### Component Status

| Component | Status | Notes |
|-----------|--------|-------|
| Sanity CMS | ✅ Live | Project ID: 4t6f8tmh |
| n8n | ✅ Live | Docker container |
| Middleware API | ✅ Live | localhost:8000 |
| Redis Queue | ✅ Live | Docker container |
| ComfyUI | ✅ Ready | Manual start required |
| **CosyVoice** | ✅ **Golden Env** | `cosyvoice:v3-vpn` - Trembling fixed! |
| Remotion | ✅ Live | Renders via middleware |
| Nginx Assets | ✅ Live | Docker, port 8081 |
| **LTX-2 Agent** | ✅ **VERIFIED** | 20s HD Video on RTX 4090 |
| Perception Layer | 🔄 Starting | yt-dlp, RSSHub, Crawl4AI |

---

## 🆕 Recent Updates (2026-01-07)

### CosyVoice v3 Golden Environment ✅
The trembling/shaky audio issue has been **resolved**:

| Feature | Status |
|---------|--------|
| English TTS | ✅ 211KB, 2.8s |
| Chinese TTS | ✅ 351KB, 2.85s |
| Zero-shot cloning | ✅ Working |

**Fixes Applied:**
1. `n_timesteps=50` for audio stability
2. `server.py` temp file handling for CosyVoice3 API
3. `ruamel.yaml<0.18` + `x-transformers` dependencies
4. Model config fix (cosyvoice3.yaml)

**Docker Image:** `cosyvoice:v3-vpn`

### CosyVoice API Endpoint
```
POST http://localhost:50000/inference_zero_shot
Content-Type: multipart/form-data

- tts_text: Text to synthesize (include <|endofprompt|> for CosyVoice3)
- prompt_text: Reference prompt with <|endofprompt|>
- prompt_wav: Reference audio file (binary)
```

---

## 📋 Completed Phases

### Phase 1-3: Infrastructure ✅
- Docker, Redis, Postgres configured
- Volume mounts on SSD (`/mnt/data_ssd`)
- 8 Sanity schemas created

### Phase 4-5: n8n & DevOps ✅
- 4 workflows deployed
- Git LFS configured
- Backup scripts created

### Phase 6-7: GPU Integration ✅
- Async middleware with Redis queue
- ComfyUI + CosyVoice drivers
- Async middleware with Redis queue
- ComfyUI + CosyVoice drivers
- End-to-end test passed

### Phase 7: LTX-2 Video Generation ✅
- **Verified**: 20s HD (1280x720) Video + Audio on RTX 4090
- **Configuration**: `--cache-none --reserve-vram 8 --fp8`
- **Result**: Native HD generation without OOM

### Phase 10: Perception Layer (In Progress) 🔄
- Services deploying: `rsshub`, `ytdlp`, `crawl4ai`
- Goal: Automated source tracking & asset collection

### Phase 8: Remotion Engine ✅
- Video composition from JSON timeline
- Nginx asset server

### Phase 9: DeepSeek Brain ✅
- Chain-of-thought: Analyst → Writer → Director → Editor
- Full pipeline generates 60-second MP4

### Phase 10: CosyVoice Golden Environment ✅ (Partial)
- Trembling audio fixed
- Docker image built and running

---

## 🚧 Not Yet Implemented

| Feature | Priority | Notes |
|---------|----------|-------|
| Real avatar in pipeline | High | LongCat ready, needs wiring |
| CosyVoice in n8n workflow | High | API working, needs integration |
| Subtitle sync | Medium | Need word timestamps |
| Auto-publish | Low | Social media APIs |

---

## 🎯 Recommended Next Steps

1. **Wire CosyVoice to n8n workflow**
   - Call `inference_zero_shot` after Writer stage
   - Use audio duration for timeline

2. **Generate real avatar video**
   - Use LongCat LoRA with CosyVoice audio
   - Replace placeholder videos

3. **Production cleanup**
   - Rotate API keys
   - Set up proper secrets management

---

## 📁 Key Files

| File | Purpose |
|------|---------|
| `docker/cosyvoice/Dockerfile` | CosyVoice Golden Environment |
| `n8n/workflows/3_Orchestrator_V8_8.json` | Main brain workflow |
| `middleware/worker.py` | GPU task processor |
| `rendering/src/Composition.tsx` | Video composition |
| `docker-compose.yml` | Service definitions |

---

## 🔑 Access Points

| Service | URL |
|---------|-----|
| n8n | http://localhost:5678 |
| Sanity Studio | http://localhost:3333 |
| Middleware API | http://localhost:8000 |
| CosyVoice | http://localhost:50000 |
| Asset Server | http://localhost:8081 |
| ComfyUI | http://localhost:8188 |

---

## 📊 Last Successful Runs

| Date | Task | Result |
|------|------|--------|
| 2026-01-07 16:23 | CosyVoice English TTS | ✅ 211KB in 2.80s |
| 2026-01-07 16:28 | CosyVoice Chinese TTS | ✅ 351KB in 2.85s |
| 2026-01-04 09:34 | Full Remotion Render | ✅ 2.5MB MP4 (60s) |
