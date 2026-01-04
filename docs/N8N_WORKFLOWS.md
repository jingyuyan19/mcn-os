# n8n Workflow Guide

**Location:** `/n8n/workflows/`  
**Purpose:** Automation orchestration and AI decision-making

---

## Available Workflows

| Workflow | Purpose |
|----------|---------|
| `1_Schedule_Poller.json` | Poll Sanity for scheduled content |
| `2_Post_Generator.json` | Create new posts in Sanity |
| `3_Orchestrator_V8_8.json` | **Main Brain** - DeepSeek AI pipeline |
| `3_Video_Renderer.json` | Direct video render trigger |

---

## Main Workflow: `3_Orchestrator_V8_8.json`

### Node Flow

```
On Click → Fetch Prompts → Setup Context → Prep Analyst → Analyst API
    → Prep Writer → Writer API → Prep Director → Director API
    → Editor Logic → Submit Render Task
```

### Node Descriptions

| Node | Type | Purpose |
|------|------|---------|
| `On Click` | Manual Trigger | Start workflow manually |
| `Fetch Prompts` | HTTP Request | GET prompts from Sanity |
| `Setup Context` | Code | Extract prompts, prepare input |
| `Prep Analyst` | Code | Build DeepSeek request payload |
| `Analyst API` | HTTP Request | Call DeepSeek for analysis |
| `Prep Writer` | Code | Merge analyst output + writer prompt |
| `Writer API` | HTTP Request | Call DeepSeek for script |
| `Prep Director` | Code | Merge script + director prompt |
| `Director API` | HTTP Request | Call DeepSeek for visual plan |
| `Editor Logic` | Code | Calculate timeline frames |
| `Submit Render Task` | HTTP Request | POST to Middleware API |

---

## DeepSeek Chain-of-Thought

### Stage 1: Analyst
**Input:** Raw content (article, PDF text)  
**Output:**
```json
{
  "summary": "Core concept summary",
  "key_points": ["Point 1", "Point 2"],
  "usp": ["Selling point 1", "Selling point 2"]
}
```

### Stage 2: Writer
**Input:** Analyst output + Artist persona  
**Output:**
```json
[
  { "id": 1, "script": "Hook line...", "visual_intent": "A-Roll" },
  { "id": 2, "script": "Content...", "visual_intent": "B-Roll" }
]
```

### Stage 3: Director
**Input:** Script array  
**Output:**
```json
[
  { "id": 1, "type": "avatar", "script": "..." },
  { "id": 2, "type": "wan_video", "visual_prompt": "cinematic shot...", "script": "..." }
]
```

### Stage 4: Editor (JavaScript)
**Input:** Director plan  
**Output:** Remotion timeline JSON

---

## HTTP Request Node Configuration

### Modern n8n (v1.0+) Format
```json
{
  "method": "GET",
  "url": "https://api.example.com/endpoint",
  "sendQuery": true,
  "queryParameters": {
    "parameters": [
      { "name": "key", "value": "value" }
    ]
  },
  "sendHeaders": true,
  "headerParameters": {
    "parameters": [
      { "name": "Authorization", "value": "Bearer token" }
    ]
  }
}
```

### Expression Syntax
- Access previous node: `$('NodeName').first().json`
- Access current item: `items[0].json`
- Expression wrapper: `={{ expression }}`

---

## Sanity Query Integration

**Fetch Prompts:**
```
GET https://4t6f8tmh.api.sanity.io/v2024-01-01/data/query/production
?query=*[_type == "prompt_config"]
```

**Write Data (requires auth):**
```
POST https://4t6f8tmh.api.sanity.io/v2024-01-01/data/mutate/production
Authorization: Bearer sk...
```

---

## Middleware Integration

**Submit Task:**
```
POST http://172.17.0.1:8000/submit_task
Content-Type: application/json

{
  "task_type": "remotion_render",
  "priority": 50,
  "payload": { "timeline": { ... } }
}
```

> **Note:** Use `172.17.0.1` (Docker gateway) when calling from n8n container to host middleware.

---

## Importing Workflows

1. Open n8n: `http://localhost:5678`
2. Click **Import** (top right)
3. Paste JSON or upload file
4. Save & Activate

---

## Common Issues

| Issue | Solution |
|-------|----------|
| `nodeName` error | Use Manual Trigger, not Start node |
| Empty query params | Use `queryParameters.parameters[]` format |
| Expression not resolved | Wrap in `={{ }}` |
| Can't reach middleware | Use `172.17.0.1:8000` in Docker |
