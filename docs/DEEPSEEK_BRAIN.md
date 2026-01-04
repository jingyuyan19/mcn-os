# Master Architecture V8.0: The "DeepSeek" Brain

**Core Philosophy**: "Separation of Concerns" between Creativity (LLM) and Precision (Code).
We do not ask the LLM to calculate timestamps. We ask it to generating *intent*, and use JavaScript to calculate *execution*.

## 1. The Four-Stage Pipeline (n8n)

### 🟢 Stage 1: The Analyst (De-Noise)
*   **Task**: Turn chaotic input (PDF, Web, Text) into structured Commercial Intelligence.
*   **Engine**: DeepSeek V3 (LLM).
*   **Input**: Raw Source.
*   **Output (JSON)**:
    ```json
    {
      "summary": "Core concept...",
      "key_points": [],
      "usp": ["Selling Point 1", "Selling Point 2"],
      "risk_warning": "..."
    }
    ```

### 🟡 Stage 2: The Writer (Persona & Hook)
*   **Task**: Apply Artist "DNA" (Tone, Voice) to the Dry Facts. Build the "Golden Triad" structure.
*   **Engine**: DeepSeek V3 (LLM).
*   **Input**: Analyst JSON + Artist Context (from Sanity).
*   **Output (JSON)**:
    ```json
    [
      { "id": 1, "script": "Hook...", "visual_intent": "A-Roll" },
      { "id": 2, "script": "Content...", "visual_intent": "B-Roll" }
    ]
    ```

### 🔴 Stage 3: The Director (Visual Planning)
*   **Task**: Translate "Visual Intent" into "Execution Paths" (File Paths / Prompts).
*   **Engine**: DeepSeek V3 (LLM).
*   **Input**: Script JSON + Available Assets.
*   **Output (JSON - "The Call Sheet")**:
    ```json
    [
      { "id": 1, "type": "avatar", "src": null },
      { "id": 2, "type": "wan_video", "visual_prompt": "cinematic stock crash..." },
      { "id": 3, "type": "product_vfx", "manual_asset": "client_product.png" }
    ]
    ```

### 🔵 Stage 4: The Editor (Precision Assembly)
*   **Task**: Mathematical alignment of Audio Time -> Video Frames.
*   **Engine**: **JavaScript (n8n Code Node)**.
*   **Input**: "The Call Sheet" + `audio_duration` (from middleware/TTS).
*   **Logic**:
    *   Total Frames = `duration * fps`.
    *   Shot Weight = `char_length / total_chars`.
    *   Shot Frames = `Total Frames * Shot Weight`.
*   **Output (JSON - "Remotion Timeline")**:
    *   The exact payload `composition.tsx` needs.

## 2. Infrastructure Changes

### Sanity CMS (`prompt_config`)
We will move prompts out of code and into the CMS.
*   **Schema**: `prompt_config`
    *   `role`: Analyst | Writer | Director
    *   `template`: The raw prompt string with `{{handlebars}}` variables.
    *   `version`: For A/B testing prompts.

### Middleware
*   **No Change to Logic**: The middleware remains the "Muscle". It blindly executes the "Call Sheet" (Generate Image, Render Video).
*   **Change to Flow**: The *Director* (n8n) tells the Middleware *what* to make.

## 3. Implementation Steps (Phase 9)

1.  **Sanity**: Create `prompt_config` schema.
2.  **Seeding**: Input the V8.0 Prompts into Sanity.
3.  **n8n**:
    *   Set up DeepSeek Credentials (OpenAI Compatible).
    *   Build the "Chain of Thought" Workflow.
    *   Implement the "Editor" JS Node.
4.  **Verification**: End-to-End run with a complex inputs (e.g. legal PDF).
