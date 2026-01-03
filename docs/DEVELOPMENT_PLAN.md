# 🗺️ Digital MCN OS: Incremental Development Plan

> **Goal:** Build a robust, commercial-grade AI Content Factory.
> **Constraint:** Single RTX 4090. Strict VRAM management.
> **Methodology:** Unit Testing -> API Encapsulation -> Integration.

---

## 🟢 Phase 1: Infrastructure & Atomic Units (基建与原子能力)

**目标**：确保 Docker 环境正常，且基础 AI 模型（声音、图片、背景）能独立运行。

### 1.1 Docker & Storage Foundation
* **Task:** Create `docker-compose.yml` (n8n, Redis). Ensure `/opt/mcn-os/assets` volume is writable by both Host and Docker.
* **Verification:** `docker ps` is green. Files created in Host appear in Container.

### 1.2 The Voice (CosyVoice 3.0)
* **Task:** Build Docker image from source (`FunAudioLLM/CosyVoice`). Tag: `cosyvoice:v3.0`.
* **Model:** Download `FunAudioLLM/Fun-CosyVoice3-0.5B-2512` to `/opt/mcn-os/assets/models`.
* **Test:** Manually `curl` the local API with text + emotion seed.
* **Success:** A `.wav` file is generated using the 3.0 model.

### 1.3 The Photographer (Flux.1-Dev FP8)
* **Task:** Install ComfyUI. Build Workflow: **Flux.1-Dev (FP8)** + **PuLID** (Face ID).
* **Test:** Generate 5 images of "Old K" in different suits.
* **Success:** Faces are consistent. Generation time < 15s. Save as `workflow_flux.json`.

### 1.4 The Atmosphere (Wan 2.1 & Depth)
* **Task A:** Build `workflow_wan.json` (Text to Video, 4s).
* **Task B:** Build `workflow_depth.json` (Image -> Depth Anything -> 3D Ken Burns).
* **Success:** Wan runs without OOM. Product logo moves in 3D without hallucination.

---

## 🟡 Phase 2: The Complex Chains (复杂合成验证)

**目标**：攻克最难的 LongCat（口型同步），因为它最吃显存，必须单独调优。

### 2.1 The Actor (LongCat)
* **Task:** Build Workflow: `Load Image` (from Phase 1.3) + `Load Audio` (from Phase 1.2) -> `LongCat Node` -> `Video`.
* **VRAM Tuning:** You might need to unload Flux model logic to fit LongCat.
* **Success:** A video with perfect lip-sync. Save as `workflow_longcat.json`.

### 2.2 API Preparation
* **Task:** Convert all workflows to **API Format**. Identify dynamic inputs (Seed, Text, File Paths).

---

## 🟠 Phase 3: The Middleware Layer (调度层)

**目标**：告别 UI 操作，用 Python 代码控制 4090，并实现显存互斥锁。

### 3.1 Redis Lock Manager
* **Task:** Write `middleware/lock_manager.py`. Implement `acquire_lock(priority)` and `release_lock()`.

### 3.2 GPU Server (FastAPI)
* **Task:** Write `middleware/server.py`.
* **Logic:** `POST /submit_task` -> Acquire Lock -> `torch.cuda.empty_cache()` -> Send JSON to ComfyUI -> Wait -> Release Lock.
* **Success:** Trigger a video generation via Postman/Curl.

---

## 🔵 Phase 4: The Rendering Engine (合成层)

**目标**：用代码写视频。

### 4.1 Mock Development
* **Task:** Create a dummy JSON file (`timeline_mock.json`) representing a video structure.

### 4.2 Remotion Logic
* **Task:** Build `<Composition />` component.
* **Logic:**
    * Track 1: Avatar Video.
    * Track 2: Product Overlay (if time matches).
    * Track 3: Subtitles.
* **Success:** `npx remotion render` outputs a valid MP4 using mock assets.

---

## 🟣 Phase 5: The Brain & Orchestration (集成层)

**目标**：连接 n8n、Sanity 和 DeepSeek。

### 5.1 Sanity & DeepSeek
* **Task:** Deploy CMS Schemas. Setup n8n to call DeepSeek API.
* **Prompt Engineering:** Tune DeepSeek to output the **exact JSON format** needed by Phase 4.

### 5.2 End-to-End Flow
* **Task:** Connect the dots in n8n:
`Trigger` -> `DeepSeek` -> `Middleware API` (Generate Assets) -> `Remotion CLI` (Render).
* **Success:** One click in n8n produces a final video.

---

## 🔴 Phase 6: Commercial & Distro (商业化与分发)

**目标**：实现 VIP 插队和真机分发。

### 6.1 Priority Interrupt
* **Task:** Update Middleware to handle `priority=100` (Jump Queue).

### 6.2 Phone Farm
* **Task:** Write `publish.py` using Scrcpy/ADB.
* **Success:** Video auto-uploads to TikTok via physical phone.
