# Remotion Composition Guide

**Location:** `/rendering/`  
**Purpose:** Video composition from JSON timeline

---

## Architecture

```
Timeline JSON → Composition.tsx → Remotion CLI → MP4
```

---

## Timeline Format

```typescript
interface Timeline {
  width: number;           // 1080 (vertical) or 1920 (horizontal)
  height: number;          // 1920 (vertical) or 1080 (horizontal)
  fps: number;             // Usually 30
  durationInFrames: number;// Total frames (fps * seconds)
  clips: Clip[];           // Visual layers
  subtitles?: Subtitle[];  // Text overlays
  audioSrc?: string;       // Main voice track (relative path)
  bgmSrc?: string;         // Background music (relative path)
}

interface Clip {
  type: 'avatar' | 'image' | 'video' | 'wan_video';
  src: string;             // RELATIVE path (e.g., "videos/clip.mp4")
  startFrame: number;
  durationFrames: number;
  layer: number;           // 0 = bottom, higher = top
  style?: CSSProperties;   // Optional styling
}

interface Subtitle {
  text: string;
  startFrame: number;
  endFrame: number;
}
```

---

## Key Files

| File | Purpose |
|------|---------|
| `src/Composition.tsx` | Main video composition logic |
| `src/types.ts` | TypeScript interfaces |
| `src/Root.tsx` | Remotion root configuration |
| `src/index.tsx` | Entry point |
| `render.ts` | CLI render script |

---

## Asset Server Integration

**IMPORTANT:** All asset paths in the timeline must be **RELATIVE**.

The composition prepends `ASSET_HOST`:
```typescript
const ASSET_HOST = 'http://localhost:8081/assets/';

// In composition:
<Video src={`${ASSET_HOST}${clip.src}`} />

// Timeline clip should use:
{ "src": "videos/avatar.mp4" }  // ✅ Correct
{ "src": "http://localhost:8081/assets/videos/avatar.mp4" }  // ❌ Wrong
```

---

## Layer System

| Layer | Content |
|-------|---------|
| 0 | Base avatar (full video) |
| 5 | Background B-roll |
| 10 | Foreground overlays |
| 20 | Subtitles |

---

## Rendering Process

### Via Middleware (Production)
```json
POST http://localhost:8000/submit_task
{
  "task_type": "remotion_render",
  "payload": {
    "timeline": { ... }
  }
}
```

### Direct CLI (Debug)
```bash
cd rendering
npx remotion render src/index.tsx MainVideo --props='{"timeline": {...}}'
```

---

## Middleware Integration

**File:** `middleware/lib/remotion_driver.py`

**Process:**
1. Receives timeline JSON
2. Writes to `assets/output/render_{task_id}.json`
3. Calls `npx ts-node render.ts <json_path> <output_path>`
4. Returns MP4 path

---

## Composition Logic

```tsx
// 1. Audio layers (bottom)
{timeline.audioSrc && <Audio src={`${ASSET_HOST}${timeline.audioSrc}`} />}
{timeline.bgmSrc && <Audio src={`${ASSET_HOST}${timeline.bgmSrc}`} volume={0.1} loop />}

// 2. Video clips (sorted by layer)
{clips.sort((a, b) => a.layer - b.layer).map(clip => (
  <Sequence from={clip.startFrame} durationInFrames={clip.durationFrames}>
    <Video src={`${ASSET_HOST}${clip.src}`} />
  </Sequence>
))}

// 3. Subtitles (top)
{timeline.subtitles?.map(sub => (
  <Sequence from={sub.startFrame} durationInFrames={sub.endFrame - sub.startFrame}>
    <div className="subtitle">{sub.text}</div>
  </Sequence>
))}
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "net::ERR_BLOCKED_BY_ORB" | Asset path doubled - use relative paths only |
| "delayRender timeout" | Video file missing or 404 |
| "VRAM exhausted" | Reduce concurrency, use CPU render |
| Black frames | Check video codec compatibility |

---

## Performance Settings

```typescript
// In render.ts
await renderMedia({
  composition,
  outputLocation,
  codec: 'h264',
  concurrency: 1,        // CPU-safe for shared GPU
  chromiumOptions: {
    gl: 'angle',
  },
});
```
