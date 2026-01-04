# Phase 9: Full End-to-End Test (The Orchestrator)

## Goal
Create the "Brain" of the operation: an n8n workflow (`3_Orchestrator`) that automates the entire content creation lifecycle without human intervention.

## Workflow Logic (`3_Orchestrator.json`)

### 1. Trigger & Context
- **Trigger**: Manual (for now) or Schedule.
- **Input**: A Topic or "Pending" post ID from Sanity.

### 2. Asset Generation (Middleware)
- **Image Gen**:
  - Call `POST /submit_task` -> `image_generate` (Flux).
  - Loop/Wait until status `completed`.
  - Result: `http://asset-server/outputs/uuid.png`.
- **Script Gen** (Mocked or Simple for MVP):
  - Use simple text based on the topic.

### 3. Rendering (Middleware)
- **Timeline Construction**:
  - Create JSON payload with:
    - `clips`: [{ type: 'image', src: 'uuid.png', duration: 90 }]
    - `subtitles`: [{ text: "Topic Title", ... }]
    - `audio`: (Optional, silent for MVP if TTS not ready)
- **Video Render**:
  - Call `POST /submit_task` -> `remotion_render`.
  - Loop/Wait until status `completed`.
  - Result: `http://asset-server/outputs/render_uuid.mp4`.

### 4. Publishing (Sanity)
- **Upload Asset**:
  - Download MP4 from `asset-server` (inside n8n).
  - Upload to Sanity API (`POST /assets/files/...`).
  - Get `file-asset-id`.
- **Update Post**:
  - Patch the Sanity document with the new video asset.
  - Set status to `ready_to_schedule` or `published`.

## Changes Required

### middleware/worker.py
- Ensure `image_generate` returns the *relative* path or full URL that `remotion_render` can access.
- Currently, `image_generate` saves to `assets/output`. `remotion_render` expects URLs that Nginx serves? Or local paths?
    - *Correction*: `Composition.tsx` uses `ASSET_HOST` + `src`.
    - If `src` is `outputs/foo.png`, `ASSET_HOST` is `http://localhost:8081/assets/`.
    - So full URL is `http://localhost:8081/assets/outputs/foo.png`.
    - We need to ensure the "src" passed to Remotion is relative to the `assets/` root.

### n8n
- Create `3_Orchestrator.json`.

## Verification Plan
1. Trigger Workflow.
2. Watch n8n Execution.
3. Verify Image created.
4. Verify Video created (using that image).
5. Verify Video appears in Sanity Studio.
