# Sanity CMS Schema Reference

**Location:** `/sanity-studio/`  
**Project ID:** `4t6f8tmh`  
**Dataset:** `production`

---

## Schema Overview

| Schema | Purpose | Key Fields |
|--------|---------|------------|
| `artist` | Digital persona | name, voice, wardrobe, studio |
| `schedule` | Content timing | artist, sources, cron |
| `source` | Content sources | url, extraction_config |
| `post` | Video projects | script, storyboard, status |
| `voice` | TTS configuration | service, reference_audio |
| `wardrobe` | Character clothing | comfy_payload |
| `studio` | Background setting | comfy_payload |
| `prompt_config` | AI prompts | role, template, version |

---

## Schema Details

### `artist.ts`
The central persona definition.

```typescript
{
  name: string,
  slug: slug,
  personality: text,        // Character description
  voice: reference<voice>,
  wardrobe: reference<wardrobe>,
  studio: reference<studio>,
  avatar_seed: number,      // For consistent generation
  social_handles: {
    platform: 'douyin' | 'xiaohongshu' | 'weixin',
    handle: string
  }[]
}
```

### `schedule.ts`
Automated content generation schedule.

```typescript
{
  title: string,
  artist: reference<artist>,
  sources: reference<source>[],
  cron_expression: string,    // e.g., "0 9 * * *"
  is_active: boolean,
  visual_config: {
    aspect_ratio: '9:16' | '16:9',
    style_preset: string
  }
}
```

### `source.ts`
Content input configuration.

```typescript
{
  name: string,
  source_type: 'rss' | 'api' | 'manual',
  url: url,
  extraction_config: {
    selector: string,         // CSS selector for scraping
    fields: string[]
  }
}
```

### `post.ts`
Generated video project.

```typescript
{
  title: string,
  status: 'draft' | 'generating' | 'review' | 'published',
  artist: reference<artist>,
  created_from_schedule: reference<schedule>,
  script: text,
  storyboard: {
    scene_id: number,
    script_line: text,
    visual_type: 'avatar' | 'b_roll' | 'product',
    visual_prompt: string,
    generated_asset: file
  }[],
  final_video: file,
  published_urls: {
    platform: string,
    url: url,
    published_at: datetime
  }[]
}
```

### `voice.ts`
TTS voice configuration.

```typescript
{
  name: string,
  service: 'cosyvoice' | 'azure',
  reference_audio: file,      // For voice cloning
  voice_id: string,           // Service-specific ID
  settings: {
    speed: number,
    pitch: number
  }
}
```

### `wardrobe.ts`
Character appearance.

```typescript
{
  name: string,
  description: text,
  comfy_payload: object,      // ComfyUI workflow params
  preview_image: image
}
```

### `studio.ts`
Background environment.

```typescript
{
  name: string,
  description: text,
  comfy_payload: object,      // ComfyUI workflow params
  cached_video: file,         // Pre-rendered background
  preview_image: image
}
```

### `prompt_config.ts` ⭐
AI prompt management for DeepSeek.

```typescript
{
  role: 'Analyst' | 'Writer' | 'Director',
  template: text,             // Prompt with {{handlebars}}
  version: string,            // For A/B testing
  is_active: boolean
}
```

**Template Variables:**
- `{{source_type}}` - Type of content source
- `{{artist_name}}` - Character name
- `{{artist_persona}}` - Personality description
- `{{post_type}}` - routine, promotion, breaking

---

## GROQ Queries

### Fetch all prompts
```groq
*[_type == "prompt_config" && is_active == true]
```

### Fetch artist with relations
```groq
*[_type == "artist" && slug.current == $slug][0] {
  ...,
  voice->,
  wardrobe->,
  studio->
}
```

### Fetch pending posts
```groq
*[_type == "post" && status == "draft"] | order(_createdAt desc)
```

---

## API Access

### Read (Public)
```bash
curl "https://4t6f8tmh.api.sanity.io/v2024-01-01/data/query/production?query=*[_type==\"artist\"]"
```

### Write (Requires Token)
```bash
curl -X POST \
  -H "Authorization: Bearer $SANITY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"mutations": [{"create": {...}}]}' \
  "https://4t6f8tmh.api.sanity.io/v2024-01-01/data/mutate/production"
```

---

## Local Development

```bash
cd sanity-studio
npm install
npm run dev     # http://localhost:3333
```

---

## MCP Integration

The system includes Sanity MCP for AI agent access:
- Query documents
- Create/update content
- Upload assets

See `SETUP_GITHUB_MCP.md` for configuration.
