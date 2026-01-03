# Architecture Design: Digital MCN Operating System
**"The Autonomous Media Enterprise"**

## 1. Executive Summary
This document outlines the architecture for a fully automated, headless Multi-Channel Network (MCN). The system operates as a **factory** that manages a matrix of AI "Artists" (data objects) to produce content at scale. It distinguishes itself through a "Two-Speed" operating model that prioritizes commercial reliability over viral creativity.

## 2. Core Operating Principles

### A. Configuration as Artist
An "Artist" is not a person or a fixed code module, but a **Data Configuration** loaded at runtime.
- **Soul**: System Prompt (Personality, Tone, Niche).
- **Body**: Visual Anchors (FaceID, LoRA), VoiceID (CosyVoice).
- **Implication**: The factory hardware is improved independently of the "Talent" roster. Talent can be swapped instantly based on market trends.

### B. The Two-Speed Engine (Priority Logic)
The system resource scheduler (GPU/CPU) operates on a strict priority basis.

| Feature | Speed 1: Daily Traffic | Speed 2: VIP Lane |
| :--- | :--- | :--- |
| **Trigger** | Scheduled / Trend Detection | Manual "Order" Input |
| **Goal** | Viral Reach, Engagement | Client Satisfaction, Conversion |
| **Logic** | "Creative Spin" (Generative) | "Strict Compliance" (Deterministic) |
| **Visual Tech** | Generative AI (Flux, Wan, LongCat) | Parallax/CV (Start/End with Real Assets) |
| **Priority** | **Low (Interruptible)** | **High (Critical)** |

### C. The Air-Gap Distribution
To mimic organic human behavior and avoid automated detection:
- **No API Uploads**: The system produces polished MP4s.
- **Physical Sync**: Files are synced via Syncthing to a local "Phone Farm".
- **Human Touch**: Final publishing is triggered physically or via simulated precision touch on real devices.

---

## 3. System Architecture

### Layer 1: The Headquarters (Control Plane)
- **Technology**: **Sanity.io** (Headless CMS)
- **Role**: Validates and stores the "Truth".
- **Data Models**:
    - `Artist`: The DNA of the virtual influencer.
    - `Script`: The content roadmap.
    - `Order`: The commercial contract (Sponsorship Brief).

### Layer 2: The Conductor (Orchestration)
- **Technology**: **n8n** (Workflow Automation)
- **Role**: Connects all discrete services. Manages the lifecycle of a job from trigger to delivery.
- **Key Workflows**:
    - `Daily_Grind`: Cron -> Firecrawl -> DeepSeek -> Produce.
    - `VIP_Rush`: Webhook (Sanity) -> DeepSeek (Audit) -> Priority Produce.

### Layer 3: The Brain (Cognition)
- **Technology**: **DeepSeek-V3** (via API)
- **Role**:
    - **Scriptwriter**: Transforms raw news into persona-based scripts.
    - **Director**: Outputs JSON directions for the visual engine (Camera angles, mood).
    - **Compliance Officer**: Checks generated content against client briefs (VIP Lane).

### Layer 4: The Factory (Production)
Managed by a **Python Middleware** to handle the single-GPU constraint.

#### A. Resource Scheduler (Redis)
- Implements the **Priority Queue**.
- Locks the GPU (NVIDIA 4090) to prevent crashing from concurrent heavy loads (e.g., Running Flux + CosyVoice simultaneously).

#### B. Visual Engine (Hybrid)
- **Generative (Creative)**: ComfyUI executing Flux/Wan flows for "B-Roll" and LongCat for "A-Roll" (talking head).
- **Deterministic (Truth)**: Remotion + DepthAnything for "Product Shots" (2.5D Parallax).

#### C. Audio Engine
- **Technology**: **CosyVoice 2** (Docker)
- **Role**: Text-to-Speech with emotional embedding.

### Layer 5: Post-Production & Distribution
- **Technology**: **Remotion** (React-based Video)
- **Role**: The "Editor". Stitches generated clips, adds subtitles, music, and effects based on the JSON "Edit Decision List" from the Brain.
- **Output**: MP4 video file moved to `Syncthing/Outbox`.

---

## 4. Data Flow Example: The VIP Order

1.  **Input**: Admin uploads a PDF Brief + VPN Logo to Sanity.
2.  **Trigger**: Sanity fires `webhook_vip_order`.
3.  **Analyze**: DeepSeek reads PDF, extracts 3 USPs (Fast, Secure, Cheap).
4.  **Suspend**: Middleware pauses any running "Daily Traffic" rendering.
5.  **Produce**:
    *   **Audio**: Generate voiceover for USPs.
    *   **Visual**: Generate "Tech Background" (Flux) + "Product Slide" (Parallax of Logo).
6.  **Assemble**: Remotion constructs the timeline.
7.  **Deliver**: Video synced to Admin's phone.
8.  **Resume**: Middleware releases GPU; "Daily Traffic" jobs resume.

## 5. Directory Structure Strategy
```text
/mcn
├── sanity/             # Control Plane Config
├── n8n/                # Workflow JSONs
├── middleware/         # Python GPU Scheduler & API Wrappers
├── visual/             # ComfyUI Workflows & Assets
├── audio/              # CosyVoice Config
├── remotion/           # Video Rendering Code
└── syncthing/          # Distribution Folder
```
