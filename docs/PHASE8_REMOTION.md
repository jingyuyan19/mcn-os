# Phase 8: The Artificial Director (Remotion Engine)

## 📌 Context
We have a "Factory" (GPU Middleware) that produces raw materials:
*   **A-Roll**: Avatar Videos (CosyVoice + SadTalker/Wan).
*   **B-Roll**: Flux/Wan generated clips.
*   **Voice**: TTS Audio.

**Objective**: Build a **CPU-based Rendering Engine** to assemble these raw materials into a final polished video, orchestrated by **DeepSeek (The Director)**.

---

## 🏗️ Architecture: The "Hamburger Model"

## 🏗️ Architecture: The "Hamburger Model" (Enhanced)

```mermaid
graph TD
    A[DeepSeek (Director)] -->|JSON Timeline| B[n8n (Producer)]
    B -->|HTTP Task| C[Middleware (Manager)]
    C -->|Queue| D[Redis]
    D -->|Pop| E[Unified Worker]
    
    subgraph "Host Machine"
        C
        E
        E -->|Exec| F[ComfyUI (GPU)]
        E -->|Exec| G[Remotion (CPU)]
    end
    
    H[Nginx (Asset Server)] -->|Serve Files| G
    
    subgraph "Docker"
        H
        A
    end
```

### 1. The Strategy
*   **Unified Media Worker**: Instead of adding an SSH connection for n8n to talk to the host, we will **teach the existing Python Worker how to render**.
    *   New Task Type: `remotion_render`.
    *   Benefit: Reuses existing Queue, Logging, and Error Handling. No SSH keys needed.
*   **CPU Safety**: The worker will run Remotion with `nice -n 15` and `concurrency: 1`.
*   **Asset Server**: Nginx serves files with strict **CORS** headers to allow Headless Chrome access.

### 2. The Director's Script (JSON Contract)
DeepSeek will output this `Timeline` structure:

```json
{
  "width": 1080,
  "height": 1920,
  "fps": 30,
  "audioSrc": "temp/voice_001.wav",
  "bgmSrc": "music/lofi_chill.mp3",
  "clips": [
    {
      "type": "avatar",
      "src": "temp/avatar_001.mp4",
      "startFrame": 0,
      "durationFrames": 1800,
      "layer": 0,
      "style": { "scale": 1.0 }
    },
    {
      "type": "product_vfx",
      "src": "sponsorships/coke_01.mp4",
      "startFrame": 450,
      "durationFrames": 150,
      "layer": 10,  // Overlays on top
      "style": { "top": 500, "scale": 0.5 }
    }
  ],
  "subtitles": [
    { "text": "This is the future of AI.", "startFrame": 0, "endFrame": 60 }
  ]
}
```

---

## 🛠️ Implementation Steps

### Step 1: Infrastructure (Nginx & Fonts)
1.  **Nginx**: Create `nginx_cors.conf` with `Access-Control-Allow-Origin *` and mount to Docker.
2.  **Fonts**: Download `NotoSansSC-Bold.otf` to `rendering/public/fonts/` (Bypass system font issues).

### Step 2: Remotion Project Setup
1.  Initialize `rendering/` (React).
2.  Install dependencies: `zod`, `@remotion/cli`, `@remotion/renderer`.
3.  **App Logic**:
    *   `src/types.ts`: Zod Definitions.
    *   `src/Composition.tsx`: Logic to handle Layers (Volume=0 for overlays) and Subtitles.
    *   `src/index.css`: Load local fonts.

### Step 3: Middleware Upgrade
1.  **Driver**: Create `middleware/lib/remotion_driver.py`.
    *   Logic: `subprocess.run(['nice', '-n', '15', 'npx', 'remotion', 'render', ...])`.
2.  **Worker**: Update `worker.py` to handle `task_type: 'remotion'`.

### Step 4: n8n "Director Mode"
Update `n8n` workflow to:
1.  **Prompt DeepSeek**: "Here is the assets list. Output JSON."
2.  **Submit Task**: POST JSON to Middleware (`/submit_task`).
3.  **Poll Status**: Wait for render completion.

---

## ❓ Final Check
*   **Fonts**: Local Bundling ✅
*   **CORS**: Nginx Config ✅
*   **Concurrency**: `nice -n 15` + `concurrency: 1` ✅
*   **Execution**: Middleware (Python) -> CLI (Node) ✅

---
