# MCN OS Current State

**Last Updated:** 2026-01-04  
**Version:** 1.0 (Phase 9 Complete)

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
| CosyVoice | ✅ Ready | Docker container |
| Remotion | ✅ Live | Renders via middleware |
| Nginx Assets | ✅ Live | Docker, port 8081 |

---

## 📋 Completed Phases

### Phase 1-3: Sanity Setup ✅
- 8 schemas created (artist, schedule, post, voice, wardrobe, studio, source, prompt_config)
- Test data seeded

### Phase 4: n8n Automation ✅
- 4 workflows: Schedule Poller, Post Generator, Video Renderer, Orchestrator V8.8

### Phase 5: DevOps ✅
- Git LFS configured
- Backup scripts created

### Phase 6: GPU Integration ✅
- Async middleware with Redis queue
- ComfyUI + CosyVoice drivers

### Phase 7: End-to-End Test ✅
- n8n → Middleware → ComfyUI verified

### Phase 8: Remotion Engine ✅
- Video composition from JSON timeline
- Nginx asset server

### Phase 9: DeepSeek Brain ✅
- Chain-of-thought: Analyst → Writer → Director → Editor
- Full pipeline generates 60-second MP4

---

## 🚧 Not Yet Implemented

| Feature | Priority | Notes |
|---------|----------|-------|
| Real avatar video | High | Currently using placeholder |
| CosyVoice in pipeline | High | Driver ready, not wired |
| Subtitle sync | Medium | Need word timestamps |
| B-roll generation | Medium | WanVideo integrated |
| Auto-publish | Low | Social media APIs |

---

## 🎯 Recommended Next Steps

1. **Replace placeholder videos**
   - Generate real avatar with LongCat LoRA
   - Create B-roll with WanVideo

2. **Wire CosyVoice**
   - Call TTS from n8n after Writer stage
   - Use audio duration for timeline

3. **Production cleanup**
   - Rotate API keys
   - Set up proper secrets management
   - Configure production n8n URL

---

## 📁 Key Files

| File | Purpose |
|------|---------|
| `n8n/workflows/3_Orchestrator_V8_8.json` | Main brain workflow |
| `middleware/worker.py` | GPU task processor |
| `rendering/src/Composition.tsx` | Video composition |
| `sanity-studio/schemaTypes/` | CMS schemas |
| `docker-compose.yml` | Service definitions |

---

## 🔑 Current Credentials

> **For development only. Rotate in production.**

| Service | Key |
|---------|-----|
| Sanity Project | 4t6f8tmh |
| DeepSeek API | sk-4756665d490f43d59223ab9567be34c8 |

---

## 📊 Last Successful Run

- **Date:** 2026-01-04 09:34
- **Task ID:** 81bc86db-3837-489c-92e6-335bf8d1bea6
- **Output:** `assets/output/render_81bc86db....mp4` (2.5MB)
- **Duration:** 60 seconds video
