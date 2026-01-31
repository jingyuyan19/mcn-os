import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

# Load .env from middleware directory
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

from lib import redis_client
from lib.gpu_manager_v2 import get_gpu_manager_v2

# Test mode toggle - set FLOW1_TEST_MODE=true to enable test features
FLOW1_TEST_MODE = os.getenv("FLOW1_TEST_MODE", "false").lower() == "true"

app = FastAPI(title="MCN GPU Scheduler (Async)", version="2.0")

class JobRequest(BaseModel):
    task_type: str       # "comfyui" | "cosyvoice"
    priority: int = 10   # 1 (Routine) | 100 (VIP)
    payload: Dict[str, Any]    # {"template": "flux_dev", "params": {...}}

@app.post("/submit_task")
def submit_job(job: JobRequest):
    """
    Enqueues a task for the background worker.
    Returns immediately with task_id.
    """
    # Validate payload for ComfyUI
    if job.task_type == "comfyui" and "template" not in job.payload:
         raise HTTPException(status_code=400, detail="ComfyUI task requires 'template' in payload")

    task_id = redis_client.enqueue_task(job.task_type, job.payload, job.priority)
    return {"status": "queued", "task_id": task_id}

@app.get("/status/{task_id}")
def check_status(task_id: str):
    info = redis_client.get_task_info(task_id)
    if not info:
        raise HTTPException(status_code=404, detail="Task not found")
    
    response = {
        "id": info["id"],
        "status": info["status"],
        "task_type": info["type"]
    }
    
    if info.get("result"):
        response["result"] = info["result"]
    
    if info.get("error"):
        response["error"] = info["error"]
        
    return response

@app.get("/health")
async def health_check():
    """Health check with GPU status."""
    try:
        manager = get_gpu_manager_v2()
        vram = manager.get_vram_status()
        gpu_ok = vram.free_mb > 1000  # At least 1GB free
        gpu_info = {
            "ok": gpu_ok,
            "free_mb": vram.free_mb,
            "used_mb": vram.used_mb,
            "temperature_c": vram.temperature_c,
        }
    except Exception as e:
        gpu_ok = False
        gpu_info = {"ok": False, "error": str(e)}

    return {
        "status": "ok",
        "mode": "async_worker",
        "gpu": gpu_info,
    }


# =============================================================================
# GPU Management Endpoints
# =============================================================================

@app.get("/gpu/status")
async def get_gpu_status():
    """
    Get comprehensive GPU status.

    Returns:
        VRAM usage, service states, lock info
    """
    manager = get_gpu_manager_v2()
    return await manager.get_status()


@app.post("/gpu/prepare-phase/{phase}")
async def prepare_gpu_phase(phase: int):
    """
    Prepare GPU for a pipeline phase.

    Automatically stops unnecessary services and starts required ones.

    Args:
        phase: Pipeline phase (1=crawl, 2=analysis, 3=tts, 4=video, 5=render)

    Returns:
        Success status
    """
    if phase < 1 or phase > 5:
        raise HTTPException(400, f"Invalid phase: {phase}. Must be 1-5.")

    manager = get_gpu_manager_v2()
    success = await manager.prepare_for_phase(phase)
    return {"success": success, "phase": phase}


@app.post("/gpu/service/{service_name}/start")
async def start_gpu_service(service_name: str):
    """
    Start a GPU service.

    Args:
        service_name: One of: comfyui, cosyvoice, vidi, ollama

    Returns:
        Success status
    """
    manager = get_gpu_manager_v2()
    if service_name not in manager.services:
        raise HTTPException(404, f"Unknown service: {service_name}")

    success = await manager.lifecycle.ensure_service(service_name)
    return {"success": success, "service": service_name}


@app.post("/gpu/service/{service_name}/stop")
async def stop_gpu_service(service_name: str, force: bool = False):
    """
    Stop a GPU service.

    Args:
        service_name: Service to stop
        force: If true, force kill

    Returns:
        Success status
    """
    manager = get_gpu_manager_v2()
    if service_name not in manager.services:
        raise HTTPException(404, f"Unknown service: {service_name}")

    success = await manager.lifecycle.stop_service(service_name, force)
    return {"success": success, "service": service_name}


@app.post("/gpu/release-all")
async def release_all_gpu_services():
    """Stop all GPU services to free VRAM."""
    manager = get_gpu_manager_v2()
    await manager.release_all()
    return {"success": True, "message": "All GPU services stopped"}


@app.post("/gpu/lock/release")
async def force_release_gpu_lock():
    """Force release GPU lock (use with caution)."""
    manager = get_gpu_manager_v2()
    released = manager.force_release_lock()
    return {"released": released}


# =============================================
# Sanity Webhook Handler
# =============================================
from pydantic import Field
import logging

logger = logging.getLogger("sanity_webhook")

from pydantic import ConfigDict

class SanityWebhookPayload(BaseModel):
    """Payload structure from Sanity webhook."""
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    
    doc_id: str = Field(..., alias="_id")
    doc_type: str = Field(..., alias="_type")
    doc_rev: Optional[str] = Field(None, alias="_rev")
    # Common fields
    status: Optional[str] = None
    title: Optional[str] = None

@app.post("/webhook/sanity")
async def handle_sanity_webhook(payload: SanityWebhookPayload):
    """
    Receives webhook notifications from Sanity CMS.
    
    Configure in Sanity Dashboard:
    - URL: http://YOUR_SERVER:8000/webhook/sanity
    - Trigger: On Create, Update
    - Filter: _type == "post"
    - Projection: {_id, _type, status, title, artist}
    """
    doc_type = payload.doc_type
    doc_id = payload.doc_id
    status = payload.status
    
    logger.info(f"📨 Sanity Webhook: {doc_type} [{doc_id}] -> status={status}")
    
    # Route based on document type and status
    if doc_type == "post":
        if status == "approved":
            # Manager approved - trigger Production Flow
            logger.info(f"🚀 Triggering Production Flow for post: {doc_id}")
            # Enqueue production task
            task_id = redis_client.enqueue_task(
                "production_flow",
                {"post_id": doc_id, "trigger": "sanity_webhook"},
                priority=50  # Higher priority for approved posts
            )
            return {"status": "production_triggered", "task_id": task_id}
        
        elif status == "draft":
            # New draft created - could trigger review notification
            logger.info(f"📝 New draft post: {doc_id}")
            return {"status": "draft_received", "post_id": doc_id}
        
        elif status == "published":
            # Post published - log for analytics
            logger.info(f"📺 Post published: {doc_id}")
            return {"status": "publish_logged", "post_id": doc_id}
    
    # Default: acknowledge but no action
    return {"status": "received", "action": "none"}


# =============================================
# Production Flow Endpoints
# =============================================

class ProductionRequest(BaseModel):
    post_id: str

@app.post("/production/start")
async def start_production(req: ProductionRequest):
    """
    Manually start production for a post.
    Usually triggered by webhook, but can be called directly for testing.
    """
    from lib.production_pipeline import ProductionPipeline
    import asyncio
    
    logger.info(f"🎬 Starting production for post: {req.post_id}")
    
    # Run production in background task
    pipeline = ProductionPipeline(req.post_id)
    
    # For now, run synchronously (in production: use background worker)
    try:
        result = await pipeline.run()
        return {"status": "success", "result": result}
    except Exception as e:
        logger.error(f"Production failed: {e}")
        return {"status": "error", "error": str(e)}

@app.get("/production/status/{post_id}")
async def get_production_status(post_id: str):
    """Check production status for a post."""
    from lib.sanity_client import get_sanity_client
    
    client = get_sanity_client()
    post = client.query(
        '*[_type == "post" && _id == $id][0] { _id, status, title, final_video_url }',
        {"id": post_id}
    )
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    return {
        "post_id": post_id,
        "status": post.get("status"),
        "video_url": post.get("final_video_url")
    }


# =============================================
# Creative Flow Endpoints
# =============================================
import os
import httpx

class AnalyzeRequest(BaseModel):
    content: str
    source_url: Optional[str] = None

class ScreenwriteRequest(BaseModel):
    analysis: Dict[str, Any]
    artist_id: str
    
class CreatePostRequest(BaseModel):
    title: str
    artist_id: str
    storyboard: Optional[List[Dict]] = None
    schedule_id: Optional[str] = None

@app.post("/creative/analyze")
async def analyze_content(req: AnalyzeRequest):
    """
    Analyze content using the Analyst LLM.
    Returns structured JSON with topic, key_points, angle, etc.
    """
    # Load analyst prompt
    prompt_path = os.path.join(os.path.dirname(__file__), "..", "prompts", "analyst.md")
    try:
        with open(prompt_path, "r") as f:
            system_prompt = f.read()
    except FileNotFoundError:
        system_prompt = "You are an AI analyst. Summarize the content into topic, key_points, and angle as JSON."
    
    # Call Ollama/OpenAI compatible endpoint
    ollama_url = os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1")
    model = os.getenv("OPENAI_MODEL_NAME", "qwen3:8b")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{ollama_url}/chat/completions",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Analyze this content:\n\n{req.content[:4000]}"}
                ],
                "temperature": 0.3
            }
        )
        result = response.json()
    
    # Extract content
    content = result.get("choices", [{}])[0].get("message", {}).get("content", "{}")
    
    # Try to parse as JSON
    import json
    try:
        # Remove any markdown code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        analysis = json.loads(content.strip())
    except json.JSONDecodeError:
        analysis = {"raw": content, "error": "Failed to parse JSON"}
    
    return {"status": "success", "analysis": analysis}

@app.post("/creative/screenwrite")
async def generate_storyboard(req: ScreenwriteRequest):
    """
    Generate a storyboard using the Screenwriter LLM.
    Returns scenes array matching scene.ts schema.
    """
    # Load screenwriter prompt
    prompt_path = os.path.join(os.path.dirname(__file__), "..", "prompts", "screenwriter.md")
    try:
        with open(prompt_path, "r") as f:
            system_prompt = f.read()
    except FileNotFoundError:
        system_prompt = "You are a screenwriter. Create a storyboard with scenes array."
    
    ollama_url = os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1")
    model = os.getenv("OPENAI_MODEL_NAME", "qwen3:8b")
    
    import json
    user_message = f"Create a storyboard for this analysis:\n\n{json.dumps(req.analysis, ensure_ascii=False)}"
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{ollama_url}/chat/completions",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                "temperature": 0.5
            }
        )
        result = response.json()
    
    content = result.get("choices", [{}])[0].get("message", {}).get("content", "{}")
    
    # Parse and validate
    try:
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        storyboard = json.loads(content.strip())
        
        # Fix common LLM typos in scene objects
        if "scenes" in storyboard:
            for scene in storyboard["scenes"]:
                # Fix typos like "scene," -> "scene_type"
                typo_keys = [k for k in scene.keys() if k.startswith("scene") and k != "scene_number" and k != "scene_type"]
                for typo in typo_keys:
                    if "scene_type" not in scene:
                        scene["scene_type"] = scene.pop(typo)
                # Fix missing scene_type - default to a_roll if has script
                if "scene_type" not in scene:
                    scene["scene_type"] = "a_roll" if scene.get("script") else "b_roll"
        
        # Validate with our validator
        from lib.validators import Storyboard
        validated = Storyboard(**storyboard)
        return {"status": "success", "storyboard": validated.model_dump()}
    except Exception as e:
        return {"status": "error", "error": str(e), "raw": content}

@app.post("/creative/create_post")
async def create_sanity_post(req: CreatePostRequest):
    """
    Create a new post in Sanity with the storyboard.
    """
    from lib.sanity_client import get_sanity_client
    
    client = get_sanity_client()
    result = client.create_post(
        title=req.title,
        artist_id=req.artist_id,
        schedule_id=req.schedule_id,
        storyboard=req.storyboard
    )
    
    return {"status": "success", "result": result}


# =============================================
# Creative Flow 2.0 - MiroThinker Deep Research
# =============================================

class MiroThinkerRequest(BaseModel):
    """Request for MiroThinker deep research and screenwriting."""
    source_url: str
    artist_id: Optional[str] = None
    artist_style: Optional[str] = None
    additional_context: Optional[str] = None
    create_post: Optional[bool] = False  # If True, create Sanity post after

@app.post("/creative/mirothinker")
async def mirothinker_research(req: MiroThinkerRequest):
    """
    Creative Flow 2.0: Deep research and screenwriting with MiroThinker.
    
    Replaces analyze + screenwrite with a single unified agent that:
    1. Scrapes and understands the source URL
    2. Researches additional context online (via Serper)
    3. Analyzes deeply with chain-of-thought reasoning
    4. Generates a comprehensive storyboard
    
    Args:
        source_url: URL of article/video to analyze
        artist_id: Sanity artist ID (optional)
        artist_style: Description of artist's style/persona
        additional_context: Extra instructions or context
        create_post: If True, automatically create Sanity post
    """
    from lib.mirothinker_client import get_mirothinker_client
    
    logger.info(f"🧠 MiroThinker research: {req.source_url}")
    
    # Get MiroThinker client
    client = get_mirothinker_client()
    
    # Check if model is available
    if not client.is_available():
        raise HTTPException(
            status_code=503,
            detail="MiroThinker model not available. Run: ollama run mirothinker"
        )
    
    try:
        # Run deep research and screenwriting
        result = await client.research_and_screenwrite(
            source_url=req.source_url,
            artist_style=req.artist_style,
            additional_context=req.additional_context
        )
        
        # Optionally create Sanity post
        if req.create_post and result.get("storyboard") and req.artist_id:
            from lib.sanity_client import get_sanity_client
            
            sanity = get_sanity_client()
            storyboard = result["storyboard"]
            
            post_result = sanity.create_post(
                title=storyboard.get("title", "Untitled"),
                artist_id=req.artist_id,
                storyboard=storyboard.get("scenes", [])
            )
            result["sanity_post"] = post_result
            logger.info(f"📝 Created Sanity post: {post_result.get('_id')}")
        
        return {
            "status": "success",
            "source_url": req.source_url,
            "storyboard": result.get("storyboard"),
            "sanity_post": result.get("sanity_post"),
            "model": result.get("model")
        }
        
    except Exception as e:
        logger.error(f"MiroThinker error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/creative/mirothinker/status")
async def mirothinker_status():
    """Check MiroThinker availability and configuration."""
    from lib.mirothinker_client import get_mirothinker_client
    
    client = get_mirothinker_client()
    
    return {
        "available": client.is_available(),
        "model": client.model,
        "serper_configured": client.serper_api_key is not None
    }


# =============================================
# Video Understanding Endpoints (Vidi2)
# =============================================

class VideoSearchRequest(BaseModel):
    video_path: str
    query: str

class VideoSearchResponse(BaseModel):
    status: str
    video_path: str
    query: str
    timestamps: List[dict]

@app.post("/video/search", response_model=VideoSearchResponse)
async def video_search(req: VideoSearchRequest):
    """
    Search for timestamps in video matching a text query.
    Uses Vidi2 temporal retrieval.
    
    Example:
        POST /video/search
        {"video_path": "/path/to/video.mp4", "query": "slicing onion"}
        
    Returns:
        {"timestamps": [{"start": "00:01:23", "end": "00:02:45"}, ...]}
    """
    from lib.vidi_client import get_client
    
    try:
        client = get_client()
        
        if not client.is_available():
            raise HTTPException(
                status_code=503,
                detail="Vidi2 model not available. Check model weights and dependencies."
            )
        
        timestamps = client.find_timestamps(req.video_path, req.query)
        
        return {
            "status": "success",
            "video_path": req.video_path,
            "query": req.query,
            "timestamps": timestamps
        }
        
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Video search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/video/status")
async def video_status():
    """Check Vidi2 availability and configuration."""
    from lib.vidi_client import get_client
    
    client = get_client()
    
    return {
        "available": client.is_available(),
        "model_path": str(client.model_path),
        "capabilities": ["temporal_retrieval", "video_qa"]
    }


# =============================================
# SENSE-THINK-CREATE Pipeline Endpoints (v2.0)
# =============================================

class DeepResearchRequest(BaseModel):
    """Request for deep web research."""
    query: str
    max_turns: int = 60
    min_scraped_pages: int = 25
    scraper: str = "jina"  # jina, firecrawl, crawl4ai

class StoryboardV2Request(BaseModel):
    """Request for Gemini storyboard generation."""
    research_report: str
    artist_persona: Dict[str, Any]
    duration_seconds: int = 60
    style: str = "informative"

@app.post("/deep_research")
async def deep_research_endpoint(req: DeepResearchRequest):
    """
    Deep web research using MiroThinker.
    
    Part of SENSE-THINK-CREATE pipeline.
    Returns structured research report with citations.
    """
    from lib.mirothinker_client import get_mirothinker_client
    
    logger.info(f"🔬 Deep research: {req.query}")
    
    client = get_mirothinker_client()
    
    if not client.is_available():
        raise HTTPException(
            status_code=503,
            detail="MiroThinker model not available"
        )
    
    try:
        result = await client.deep_research(
            query=req.query,
            max_turns=req.max_turns,
            min_scraped_pages=req.min_scraped_pages,
            scraper=req.scraper
        )
        
        return {
            "success": result.get("success", False),
            "query": req.query,
            "short_answer": result.get("short_answer", ""),
            "detailed_report": result.get("detailed_report", ""),
            "references": result.get("references", []),
            "sources_scraped": result.get("sources_scraped", 0)
        }
        
    except Exception as e:
        logger.error(f"Deep research error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate_storyboard")
async def generate_storyboard_v2(req: StoryboardV2Request):
    """
    Generate storyboard using Gemini.
    
    Part of SENSE-THINK-CREATE pipeline.
    Takes research report and artist persona, returns storyboard JSON.
    """
    from lib.gemini_client import get_gemini_client
    
    logger.info(f"🎬 Generating storyboard ({req.duration_seconds}s, {req.style})")
    
    try:
        client = get_gemini_client()
        
        storyboard = await client.generate_storyboard(
            research_report=req.research_report,
            artist_persona=req.artist_persona,
            duration_seconds=req.duration_seconds,
            style=req.style
        )
        
        return {
            "success": True,
            "storyboard": storyboard,
            "scene_count": len(storyboard)
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Storyboard generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/pipeline/status")
async def pipeline_status():
    """Check status of all SENSE-THINK-CREATE components."""
    from lib.mirothinker_client import get_mirothinker_client
    from lib.antigravity_client import get_antigravity_client
    
    miro = get_mirothinker_client()
    antigravity = get_antigravity_client()
    
    return {
        "mirothinker": {
            "available": miro.is_available(),
            "model": miro.model
        },
        "gemini": {
            "available": antigravity.is_available(),
            "model": "gemini-3-pro-high",
            "via": "Antigravity Manager (port 8045)"
        },
        "mediacrawler": {
            "path": "/home/jimmy/Documents/mcn/external/MediaCrawlerPro-Python"
        }
    }


# =============================================
# BettaFish Integration (SENSE Layer)
# =============================================

class GenerateScriptRequest(BaseModel):
    """Request for CCO-based script generation."""
    topic_id: str
    platform: str
    persona: str = "tech_blogger"
    style: str = "informative"  # informative, entertaining, dramatic
    urgency: str = "auto"  # auto/flash/normal/deep - research depth profile
    additional_context: Optional[str] = None
    create_post: bool = False
    artist_id: Optional[str] = None


def format_cco_to_prompt(cco: Dict[str, Any], persona: str, style: str) -> str:
    """Convert CCO to a rich prompt for script generation."""
    
    # Extract key data
    title = cco.get('title', 'Unknown Topic')
    velocity = cco.get('hook_vector', {}).get('trend_velocity', 'medium')
    platform = cco.get('platform', 'social media')
    
    # Vox Populi
    vox = cco.get('vox_populi', {})
    top_comments = vox.get('top_resonant', [])
    controversial = vox.get('top_controversial', [])
    slang = vox.get('vernacular_cloud', [])
    
    # Engagement
    engagement = cco.get('engagement', {})
    likes = engagement.get('likes', 0)
    comments = engagement.get('comments', 0)
    
    # Build prompt
    prompt = f"""Create a video script for this trending {platform} topic:

## TOPIC
Title: {title}
Trend Velocity: {velocity}
Engagement: {likes} likes, {comments} comments

## VOX POPULI (What the audience is saying)
"""
    
    if top_comments:
        prompt += "\n### Top Comments (use these for relatability):\n"
        for i, c in enumerate(top_comments[:3], 1):
            prompt += f"{i}. \"{c.get('text', '')[:100]}\" ({c.get('likes', 0)} likes)\n"
    
    if controversial:
        prompt += "\n### Controversial Takes (potential hook):\n"
        for i, c in enumerate(controversial[:2], 1):
            prompt += f"{i}. \"{c.get('text', '')[:100]}\" ({c.get('replies', 0)} replies)\n"
    
    if slang:
        prompt += f"\n### Use this vernacular: {', '.join(slang[:5])}\n"
    
    prompt += f"""
## REQUIREMENTS
- Persona: {persona}
- Style: {style}
- Duration: 60-90 seconds
- Format: Short-form vertical video

## OUTPUT FORMAT
Return a JSON storyboard with:
{{
  "title": "Video title",
  "hook": "Opening line to grab attention",
  "scenes": [
    {{
      "scene_number": 1,
      "type": "a_roll" or "b_roll",
      "script": "Narration text",
      "visual_prompt": "Description for video generation",
      "duration_seconds": 5-15
    }}
  ]
}}
"""
    
    return prompt


# =============================================
# MediaCrawlerPro Cookie Health Check
# =============================================
from lib.cookie_validator import validate_all_cookies, validate_platform_cookie, PLATFORMS

@app.get("/mediacrawler/check-cookies")
async def check_all_cookies(platforms: Optional[str] = None):
    """
    Validate all platform cookies using MediaCrawlerPro's pong method.
    
    Query params:
        platforms: Comma-separated list of platforms (e.g., "xhs,dy,bili")
                   If not provided, checks all 7 platforms.
    
    Returns:
        List of validation results with is_valid status for each platform.
    """
    target_platforms = None
    if platforms:
        target_platforms = [p.strip() for p in platforms.split(",") if p.strip() in PLATFORMS]
    
    results = await validate_all_cookies(platforms=target_platforms)
    
    valid_count = sum(1 for r in results if r["is_valid"])
    
    return {
        "success": True,
        "total": len(results),
        "valid": valid_count,
        "invalid": len(results) - valid_count,
        "results": results
    }


@app.get("/mediacrawler/check-cookie/{platform}")
async def check_single_cookie(platform: str, skip_update_db: bool = False):
    """
    Validate a single platform's cookie.
    
    Path params:
        platform: Platform code (xhs, dy, bili, wb, ks, zhihu, tieba)
    
    Query params:
        skip_update_db: If True, don't update account status in MySQL during validation.
                       Use this when syncing cookies to avoid re-invalidating accounts
                       that were just updated.
    """
    result = await validate_platform_cookie(platform, skip_update_db=skip_update_db)
    return {
        "success": True,
        **result
    }


@app.get("/bettafish/hot_topics")
async def get_hot_topics(
    hours: int = 24,
    limit: int = 10,
    platforms: Optional[str] = None
):
    """
    Get trending topics from BettaFish/MediaCrawlerPro.
    
    Part of SENSE layer - identifies what's trending.
    """
    from lib.bettafish_client import BettaFishClient
    
    client = BettaFishClient()
    platform_list = platforms.split(",") if platforms else None
    
    topics = client.get_hot_topics(
        hours=hours,
        limit=limit,
        platforms=platform_list
    )
    
    return {
        "success": True,
        "count": len(topics),
        "topics": topics
    }


@app.get("/bettafish/topic_cco/{platform}/{topic_id}")
async def get_topic_cco(platform: str, topic_id: str):
    """
    Get Content Context Object (CCO) for a topic.
    
    CCO includes:
    - hook_vector: trend velocity, freshness
    - vox_populi: top comments, controversial comments, slang
    - emotional_landscape: engagement metrics
    - metadata: author, url, tags
    """
    from lib.bettafish_client import BettaFishClient
    
    client = BettaFishClient()
    cco = client.get_topic_cco(topic_id, platform)
    
    if cco.get('error'):
        raise HTTPException(status_code=404, detail=cco['error'])
    
    return {
        "success": True,
        "cco": cco
    }


@app.post("/bettafish/generate_script")
async def generate_script_from_topic(req: GenerateScriptRequest):
    """
    Generate video script from BettaFish topic analysis.
    
    Full SENSE → THINK flow:
    1. Get CCO from BettaFish (SENSE)
    2. Format CCO to rich prompt
    3. Generate script with Gemini (THINK)
    4. Optionally create Sanity post (CREATE)
    """
    from lib.bettafish_client import BettaFishClient
    from lib.gemini_client import get_gemini_client
    
    logger.info(f"🎬 Generating script for {req.platform}/{req.topic_id}")
    
    # 1. Get CCO from BettaFish (SENSE)
    bettafish = BettaFishClient()
    cco = bettafish.get_topic_cco(req.topic_id, req.platform)
    
    if cco.get('error'):
        raise HTTPException(status_code=404, detail=cco['error'])
    
    # 2. Format CCO to prompt
    prompt = format_cco_to_prompt(cco, req.persona, req.style)
    
    if req.additional_context:
        prompt += f"\n\n## ADDITIONAL CONTEXT\n{req.additional_context}"
    
    # 3. Generate script with Gemini (THINK)
    try:
        gemini = get_gemini_client()
        
        # Use Gemini for script generation
        import httpx
        antigravity_url = os.getenv("ANTIGRAVITY_BASE_URL", "http://127.0.0.1:8045/v1")
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{antigravity_url}/chat/completions",
                json={
                    "model": "gemini-3-pro-high",
                    "messages": [
                        {"role": "system", "content": f"You are a {req.persona} creating viral video content. Respond with valid JSON only."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7
                }
            )
            result = response.json()
        
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "{}")
        
        # Parse JSON from response
        import json
        import re
        
        # Extract JSON from markdown code blocks if present
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
        if json_match:
            content = json_match.group(1)
        
        storyboard = json.loads(content)
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse storyboard JSON: {e}")
        return {
            "success": False,
            "error": "Failed to parse storyboard",
            "raw_content": content[:500],
            "cco": cco
        }
    except Exception as e:
        logger.error(f"Script generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    # 4. Optionally create Sanity post (CREATE)
    sanity_post = None
    if req.create_post and req.artist_id:
        try:
            from lib.sanity_client import get_sanity_client
            
            sanity = get_sanity_client()
            sanity_post = sanity.create_post(
                title=storyboard.get("title", cco.get("title", "Untitled")),
                artist_id=req.artist_id,
                storyboard=storyboard.get("scenes", [])
            )
            logger.info(f"📝 Created Sanity post: {sanity_post.get('_id')}")
        except Exception as e:
            logger.warning(f"Failed to create Sanity post: {e}")
    
    return {
        "success": True,
        "topic_id": req.topic_id,
        "platform": req.platform,
        "cco": cco,
        "storyboard": storyboard,
        "sanity_post": sanity_post
    }


@app.get("/bettafish/search")
async def search_topics(
    keyword: str,
    hours: int = 168,
    limit: int = 20,
    platforms: Optional[str] = None
):
    """
    Search for topics by keyword in BettaFish/MediaCrawlerPro data.
    """
    from lib.bettafish_client import BettaFishClient
    
    client = BettaFishClient()
    platform_list = platforms.split(",") if platforms else None
    
    results = client.search_topics(
        keyword=keyword,
        hours=hours,
        limit=limit,
        platforms=platform_list
    )
    
    return {
        "success": True,
        "keyword": keyword,
        "count": len(results),
        "results": results
    }


@app.post("/bettafish/generate_script_with_research")
async def generate_script_with_research(req: GenerateScriptRequest):
    """
    Generate video script with full MiroThinker deep research.
    
    Complete SENSE → THINK → CREATE flow:
    1. Get IR from BettaFish (SENSE)
    2. Run deep_research() with MiroThinker (THINK - 200 turns, 25+ pages)
    3. Generate storyboard with Gemini (CREATE)
    
    This is slower but produces higher-quality, web-verified content.
    For quick drafts, use /bettafish/generate_script instead.
    """
    from lib.bettafish_client import BettaFishClient
    from lib.mirothinker_client import MiroThinkerClient
    
    logger.info(f"🔬 Starting deep research for {req.platform}/{req.topic_id}")
    
    # 1. Get IR from BettaFish with urgency classification (SENSE)
    bettafish = BettaFishClient()
    
    # Auto-detect urgency or use specified
    if req.urgency == "auto":
        ir = bettafish.get_topic_with_urgency(req.topic_id, req.platform)
        urgency = ir.get('urgency', 'normal')
    else:
        ir = bettafish.get_topic_ir(req.topic_id, req.platform)
        urgency = req.urgency
    
    if ir.get('error'):
        raise HTTPException(status_code=404, detail=ir['error'])
    
    logger.info(f"📊 Using research profile: {urgency}")
    
    # 2. Generate storyboard with MiroThinker deep research (THINK → CREATE)
    mirothinker = MiroThinkerClient()
    
    result = await mirothinker.generate_storyboard_with_ir(
        ir_document=ir,
        persona=req.persona,
        style=req.style,
        urgency=urgency
    )
    
    if not result.get('success'):
        raise HTTPException(status_code=500, detail="Research failed")
    
    logger.info(f"✅ Research complete: {result.get('research_turns')} turns, {result.get('pages_scraped')} pages")
    
    # 3. Optionally create Sanity post
    sanity_post = None
    if req.create_post and req.artist_id:
        try:
            from lib.sanity_client import get_sanity_client
            sanity = get_sanity_client()
            storyboard = result.get('storyboard', {})
            sanity_post = sanity.create_post(
                title=storyboard.get("title", ir.get("title", "Untitled")),
                artist_id=req.artist_id,
                storyboard=storyboard.get("scenes", [])
            )
        except Exception as e:
            logger.warning(f"Failed to create Sanity post: {e}")
    
    return {
        "success": True,
        "topic_id": req.topic_id,
        "platform": req.platform,
        "ir": ir,
        "storyboard": result.get('storyboard'),
        "research_summary": result.get('research_summary'),
        "research_turns": result.get('research_turns'),
        "pages_scraped": result.get('pages_scraped'),
        "references": result.get('references', [])[:10],
        "sanity_post": sanity_post
    }


@app.post("/bettafish/generate_variants")
async def generate_storyboard_variants(req: GenerateScriptRequest):
    """
    Curator Pattern: Generate 3 storyboard variants for human selection.
    
    Instead of approve/reject, human selects the best variant.
    Each variant has a different style (dramatic, witty, educational)
    and is auto-scored by LLM-as-Judge.
    
    Benefits:
    - Faster human decision (selection vs judgment)
    - Implicit RLHF (learn from selections)
    - Better first-pass quality
    
    Note: Takes ~30-60s as it generates 3 storyboards + evaluations.
    """
    from lib.bettafish_client import BettaFishClient
    from lib.mirothinker_client import MiroThinkerClient
    
    logger.info(f"🎨 Generating variants for {req.platform}/{req.topic_id}")
    
    # 1. Get IR from BettaFish (SENSE)
    bettafish = BettaFishClient()
    ir = bettafish.get_topic_ir(req.topic_id, req.platform)
    
    if ir.get('error'):
        raise HTTPException(status_code=404, detail=ir['error'])
    
    # 2. Generate 3 variants with different styles (THINK)
    mirothinker = MiroThinkerClient()
    variants = await mirothinker.generate_storyboard_variants(
        ir_document=ir,
        persona=req.persona,
        count=3
    )
    
    if not variants:
        raise HTTPException(status_code=500, detail="Failed to generate variants")
    
    logger.info(f"✅ Generated {len(variants)} variants")
    
    return {
        "success": True,
        "topic_id": req.topic_id,
        "platform": req.platform,
        "ir": ir,
        "variants": variants,
        "variant_count": len(variants),
        "best_variant": variants[0] if variants else None
    }


# =============================================
# Phase 10: Full Pipeline (Topic → Video)
# =============================================

class TopicToVideoRequest(BaseModel):
    """Request for full topic-to-video pipeline."""
    topic_id: str
    platform: str
    artist_id: str  # Required: which artist to use
    urgency: str = "auto"  # flash/normal/deep
    auto_produce: bool = False  # If true, immediately start production

@app.post("/pipeline/topic_to_video")
async def topic_to_video(req: TopicToVideoRequest):
    """
    Full SENSE → THINK → CREATE → PRODUCE pipeline.
    
    1. SENSE: Get topic IR from BettaFish
    2. THINK: Research with MiroThinker (adaptive depth)
    3. CREATE: Generate storyboard via Gemini
    4. STORE: Create Sanity post with storyboard
    5. PRODUCE: (Optional) Start production pipeline
    
    This is the end-to-end flow for creating a video from a trending topic.
    """
    from lib.bettafish_client import BettaFishClient
    from lib.mirothinker_client import MiroThinkerClient
    from lib.sanity_client import get_sanity_client
    
    logger.info(f"🎬 Starting full pipeline: {req.platform}/{req.topic_id}")
    
    result = {
        "stages": {},
        "success": False
    }
    
    try:
        # 1. SENSE: Get topic with urgency classification
        bettafish = BettaFishClient()
        
        if req.urgency == "auto":
            ir = bettafish.get_topic_with_urgency(req.topic_id, req.platform)
            urgency = ir.get('urgency', 'normal')
        else:
            ir = bettafish.get_topic_ir(req.topic_id, req.platform)
            urgency = req.urgency
        
        if ir.get('error'):
            raise HTTPException(status_code=404, detail=ir['error'])
        
        result["stages"]["sense"] = {"status": "complete", "urgency": urgency}
        logger.info(f"📡 SENSE complete: {ir.get('title', 'Unknown')[:30]}...")
        
        # 2. THINK: Research with MiroThinker (adaptive depth)
        mirothinker = MiroThinkerClient()
        storyboard_result = await mirothinker.generate_storyboard_with_ir(
            ir_document=ir,
            urgency=urgency
        )
        
        if not storyboard_result.get("success"):
            raise HTTPException(status_code=500, detail="Research failed")
        
        storyboard = storyboard_result.get("storyboard", {})
        result["stages"]["think"] = {
            "status": "complete",
            "research_turns": storyboard_result.get("research_turns", 0),
            "pages_scraped": storyboard_result.get("pages_scraped", 0)
        }
        logger.info(f"🧠 THINK complete: {storyboard_result.get('research_turns', 0)} turns")
        
        # 3. EVALUATE: Score the storyboard (LLM-as-Judge)
        scores = await mirothinker.evaluate_storyboard(storyboard)
        result["stages"]["evaluate"] = {
            "status": "complete",
            "overall_score": scores.get("overall", 0),
            "issues": scores.get("issues", [])
        }
        logger.info(f"📊 EVALUATE complete: {scores.get('overall', 0):.1f}/10")
        
        # 4. CREATE: Save to Sanity as post
        sanity = get_sanity_client()
        
        # Convert storyboard scenes to Sanity format
        sanity_storyboard = []
        for i, scene in enumerate(storyboard.get("scenes", [])):
            sanity_storyboard.append({
                "_type": "object",
                "shot_number": scene.get("scene_number", i + 1),
                "duration": scene.get("duration_seconds", 5),
                "type": scene.get("type", "a_roll"),
                "script": scene.get("script", ""),
                "ai_prompt": scene.get("visual_prompt", ""),
                "is_locked": False
            })
        
        post_doc = {
            "_type": "post",
            "title": storyboard.get("title", ir.get("title", "Untitled")),
            "artist": {"_type": "reference", "_ref": req.artist_id},
            "source_content": ir.get("metadata", {}).get("original_cco", {}).get("title", ""),
            "storyboard": sanity_storyboard,
            "status": "pending_approval"  # Needs human review
        }
        
        created_post = sanity.create(post_doc)
        post_id = created_post.get("_id")
        
        result["stages"]["create"] = {
            "status": "complete",
            "post_id": post_id,
            "scene_count": len(sanity_storyboard)
        }
        logger.info(f"✨ CREATE complete: Sanity post {post_id}")
        
        # 5. PRODUCE: (Optional) Start production immediately
        if req.auto_produce:
            from lib.production_pipeline import start_production
            
            # First update status to approved
            sanity.patch(post_id, {"status": "approved"})
            
            # Start production (background task)
            import asyncio
            asyncio.create_task(start_production(post_id))
            
            result["stages"]["produce"] = {
                "status": "started",
                "note": "Production started in background"
            }
            logger.info(f"🎬 PRODUCE started for {post_id}")
        else:
            result["stages"]["produce"] = {
                "status": "pending_approval",
                "note": "Set status to 'approved' in Sanity to start production"
            }
        
        result["success"] = True
        result["post_id"] = post_id
        result["storyboard"] = storyboard
        result["evaluation"] = scores
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Pipeline failed: {e}")
        result["error"] = str(e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/pipeline/produce")
async def start_production_endpoint(post_id: str):
    """
    Start production for an approved post.
    
    Triggers: TTS → Avatar → B-Roll → Remotion Render
    """
    from lib.production_pipeline import ProductionPipeline
    from lib.sanity_client import get_sanity_client
    
    # Verify post exists and is approved
    sanity = get_sanity_client()
    post = sanity.query(
        '*[_type == "post" && _id == $id][0]',
        {"id": post_id}
    )
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    if post.get("status") != "approved":
        raise HTTPException(
            status_code=400,
            detail=f"Post status is '{post.get('status')}', must be 'approved' to start production"
        )
    
    # Start production
    pipeline = ProductionPipeline(post_id)
    
    try:
        result = await pipeline.run()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== BettaFish Sentiment Endpoints ====================

class SentimentRequest(BaseModel):
    topic_id: str
    platform: str
    max_comments: int = 100


@app.post("/bettafish/sentiment")
async def get_sentiment(request: SentimentRequest):
    """
    Analyze sentiment of topic comments using BettaFish's multilingual model.
    
    Uses tabularisai/multilingual-sentiment-analysis with 22 language support.
    Returns 5-level classification: 非常负面, 负面, 中性, 正面, 非常正面
    """
    from lib.bettafish_client import BettaFishClient
    
    client = BettaFishClient()
    result = client.get_sentiment_analysis(
        topic_id=request.topic_id,
        platform=request.platform,
        max_comments=request.max_comments
    )
    
    return {
        "success": result.get("available", False),
        "topic_id": request.topic_id,
        "platform": request.platform,
        "sentiment": result
    }


@app.post("/bettafish/enriched_cco")
async def get_enriched_cco(request: SentimentRequest):
    """
    Get CCO enriched with BettaFish sentiment analysis.
    
    This combines get_topic_cco with deep sentiment analysis for richer
    emotional landscape data.
    """
    from lib.bettafish_client import BettaFishClient
    
    client = BettaFishClient()
    cco = client.get_enriched_cco(
        topic_id=request.topic_id,
        platform=request.platform,
        include_sentiment=True
    )
    
    return {
        "success": True,
        "cco": cco
    }


# =============================================
# Perception Layer Endpoints
# =============================================

class PerceptionIngestRequest(BaseModel):
    """Request for ingesting a signal into the Perception Layer."""
    title: str
    source_type: str  # social_crawler, knowledge_base, rss_feed, manual
    platform: str     # xhs, douyin, weibo, rss, manual, etc.
    content: str      # Content snippet or summary
    url: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None  # likes, comments, shares
    keywords: Optional[List[str]] = None
    niche_id: Optional[str] = None


class ManualTopicRequest(BaseModel):
    """Manual injection of a topic (bypasses crawler)."""
    title: str
    content: str
    keywords: Optional[List[str]] = None
    niche_id: Optional[str] = None
    url: Optional[str] = None


@app.post("/perception/ingest")
async def perception_ingest(req: PerceptionIngestRequest):
    """
    Main ingestion endpoint for Perception Layer.
    
    Accepts signals from:
    - Social Crawler (MediaCrawlerPro)
    - Knowledge Base (open-notebook)
    - RSS Feed (RSSHub)
    - Manual injection
    
    Features:
    - Automatic deduplication (fingerprint + semantic)
    - Aggregation (merge duplicate signals)
    - Z-Score velocity calculation
    
    Returns:
        {"success": True, "topic_id": "...", "action": "created"|"merged"}
    """
    from lib.perception_pipeline import get_perception_pipeline
    
    logger.info(f"📡 Perception ingest: {req.title[:50]}... ({req.source_type}/{req.platform})")
    
    try:
        pipeline = get_perception_pipeline()
        result = await pipeline.ingest_signal(
            title=req.title,
            source_type=req.source_type,
            platform=req.platform,
            content=req.content,
            url=req.url,
            metrics=req.metrics,
            keywords=req.keywords,
            niche_id=req.niche_id
        )
        return result
    except Exception as e:
        logger.error(f"Perception ingest error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/perception/manual")
async def perception_manual_inject(req: ManualTopicRequest):
    """
    Manual injection endpoint (Deep Think recommendation: Pipeline #4).
    
    Allows human producers to inject topics directly,
    bypassing the crawler but using the same analysis flow.
    """
    from lib.perception_pipeline import get_perception_pipeline
    
    logger.info(f"✋ Manual topic injection: {req.title[:50]}...")
    
    try:
        pipeline = get_perception_pipeline()
        result = await pipeline.ingest_signal(
            title=req.title,
            source_type="manual",
            platform="manual",
            content=req.content,
            url=req.url,
            keywords=req.keywords,
            niche_id=req.niche_id
        )
        return result
    except Exception as e:
        logger.error(f"Manual injection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/perception/topics")
async def get_perception_topics(
    status: Optional[str] = None,
    source_type: Optional[str] = None,
    limit: int = 20
):
    """
    Get topics from the Perception Layer.
    
    Query params:
        status: Filter by status (new, analyzing, approved, rejected, scripted)
        source_type: Filter by source (social_crawler, knowledge_base, rss_feed, manual)
        limit: Max results (default 20)
    """
    from lib.sanity_client import get_sanity_client
    
    client = get_sanity_client()
    
    # Build GROQ query with filters
    filters = ['_type == "topic"']
    if status:
        filters.append(f'status == "{status}"')
    if source_type:
        filters.append(f'source_type == "{source_type}"')
    
    query = f'''
        *[{" && ".join(filters)}] | order(z_score_velocity desc, _createdAt desc) [0...{limit}] {{
            _id,
            title,
            source_type,
            status,
            z_score_velocity,
            sentiment,
            "signal_count": count(signals),
            "niche_name": niche->name,
            "artist_name": assigned_artist->name,
            _createdAt
        }}
    '''
    
    topics = client.query(query)
    
    return {
        "success": True,
        "count": len(topics) if topics else 0,
        "topics": topics or []
    }


@app.get("/perception/topic/{topic_id}")
async def get_perception_topic(topic_id: str):
    """Get a single topic with full details."""
    from lib.sanity_client import get_sanity_client
    
    client = get_sanity_client()
    
    topic = client.query(
        '*[_type == "topic" && _id == $id][0] { ..., niche->, assigned_artist-> }',
        {"id": topic_id}
    )
    
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    
    return {"success": True, "topic": topic}


@app.post("/perception/crawl-niche/{niche_id}")
async def crawl_niche_to_topics(niche_id: str):
    """
    Trigger social media crawl for a niche and create topics.
    
    Connects MediaCrawler to the Perception Pipeline:
    1. Gets niche config (keywords, platforms)
    2. Crawls each platform via MediaCrawler
    3. Creates/merges topics with deduplication
    4. Updates lastCrawledAt timestamp
    
    Path params:
        niche_id: Sanity nicheConfig document ID
    """
    from lib.perception_pipeline import get_perception_pipeline
    
    logger.info(f"🕷️ Starting niche crawl: {niche_id}")
    
    try:
        pipeline = get_perception_pipeline()
        result = await pipeline.crawl_niche_to_topics(niche_id)
        return result
    except Exception as e:
        logger.error(f"Niche crawl error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/perception/hot-topics/{niche_id}")
async def get_hot_topics(
    niche_id: str,
    time_period: str = "week",
    limit: int = 20
):
    """
    Get hot topics from crawled MySQL data for a specific niche.
    
    Uses BettaFish InsightEngine to find high-engagement content
    from crawled data, filtered by niche keywords.
    
    Path params:
        niche_id: Sanity nicheConfig document ID
        
    Query params:
        time_period: '24h', 'week', or 'year' (default: week)
        limit: Maximum topics to return (default: 20)
    """
    from lib.perception_pipeline import get_perception_pipeline
    
    logger.info(f"🔥 Getting hot topics for niche: {niche_id}")
    
    try:
        pipeline = get_perception_pipeline()
        result = await pipeline.get_hot_topics_for_niche(
            niche_id=niche_id,
            time_period=time_period,
            limit=limit
        )
        return result
    except Exception as e:
        logger.error(f"Hot topics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/perception/generate-ir/{topic_id}")
async def generate_ir_for_topic(topic_id: str, save_to_sanity: bool = True):
    """
    Generate full IR report for a topic using BettaFish InsightEngine.
    
    Path params:
        topic_id: Sanity topic document ID
        
    Query params:
        save_to_sanity: Whether to save IR to Sanity (default: True)
    """
    from lib.perception_pipeline import get_perception_pipeline
    
    logger.info(f"🔬 Generating IR for topic: {topic_id}")
    
    try:
        pipeline = get_perception_pipeline()
        result = await pipeline.generate_ir_for_topic(
            topic_id=topic_id,
            save_to_sanity=save_to_sanity
        )
        return result
    except Exception as e:
        logger.error(f"Generate IR error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/perception/niches-due-crawl")
async def get_niches_due_for_crawl():
    """
    Get niches that are due for crawling based on frequency settings.
    
    Used by n8n 10_Niche_Monitoring workflow to trigger crawls.
    """
    from lib.sanity_client import get_sanity_client
    
    client = get_sanity_client()
    niches = client.get_niches_due_for_crawl()
    
    return {
        "success": True,
        "due_count": len(niches),
        "niches": niches
    }


@app.post("/perception/process-crawler-results")
async def process_crawler_results(
    platform: str,
    results: List[Dict[str, Any]],
    niche_id: Optional[str] = None
):
    """
    Process raw MediaCrawler results into topics.
    
    Called by MediaCrawler webhook or direct integration.
    
    Body:
        - platform: xhs, douyin, weibo, etc.
        - results: Array of {title, content, url, likes, comments, shares}
        - niche_id: Optional niche to associate topics with
    """
    from lib.perception_pipeline import get_perception_pipeline
    
    logger.info(f"📥 Processing {len(results)} crawler results from {platform}")
    
    try:
        pipeline = get_perception_pipeline()
        result = await pipeline.process_crawler_results(platform, results, niche_id)
        return result
    except Exception as e:
        logger.error(f"Process results error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class RSSIngestRequest(BaseModel):
    """Request for ingesting RSS feed into perception pipeline."""
    route: str  # RSSHub route, e.g. "/weibo/hot"
    platform: str  # Platform name for topics
    niche_id: Optional[str] = None
    limit: int = 20


@app.post("/perception/rss-ingest")
async def rss_ingest(req: RSSIngestRequest):
    """
    Fetch RSS feed and ingest into perception pipeline.
    
    RSSHub routes:
    - /weibo/hot - 微博热搜
    - /bilibili/hot-search - B站热搜
    - /zhihu/hot - 知乎热榜
    - /toutiao/hot - 今日头条热榜
    - /baidu/hot - 百度热搜
    
    Body:
        route: RSSHub route
        platform: Platform name for topics
        niche_id: Optional niche to associate
        limit: Max items to fetch
    """
    from lib.rsshub_client import ingest_rss_to_topics
    
    logger.info(f"📰 RSS ingest: {req.route} → {req.platform}")
    
    try:
        result = await ingest_rss_to_topics(
            route=req.route,
            platform=req.platform,
            niche_id=req.niche_id,
            limit=req.limit
        )
        return result
    except Exception as e:
        logger.error(f"RSS ingest error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/perception/rss-hot")
async def rss_hot_topics(
    platforms: Optional[str] = None,
    limit: int = 10
):
    """
    Fetch hot topics from multiple platforms via RSSHub.
    
    Query params:
        platforms: Comma-separated list (weibo,bilibili,zhihu,toutiao,baidu)
        limit: Max items per platform
    """
    from lib.rsshub_client import get_rsshub_client
    
    client = get_rsshub_client()
    platform_list = platforms.split(",") if platforms else None
    
    items = await client.fetch_hot_topics(platforms=platform_list)
    
    return {
        "success": True,
        "count": len(items),
        "items": items[:limit * 5] if platform_list else items
    }


@app.get("/perception/rss-status")
async def rss_status():
    """Check RSSHub availability."""
    from lib.rsshub_client import get_rsshub_client
    
    client = get_rsshub_client()
    
    return {
        "available": client.is_available(),
        "url": client.base_url
    }


# =============================================
# Platform Metrics Endpoints (Phase 9)
# =============================================

@app.get("/perception/platform-metrics/{platform}/{content_id}")
async def get_platform_metrics_endpoint(platform: str, content_id: str):
    """
    Fetch real engagement metrics from social platforms.
    
    Supports:
    - bili: Bilibili (BV number or AV number)
    - dy: Douyin (aweme_id)  
    - xhs: Xiaohongshu (note_id)
    - wb: Weibo (post mid)
    - ks: Kuaishou (photo_id)
    
    Returns:
        {views, likes, comments, shares, favorites, ...}
    
    Example:
        GET /perception/platform-metrics/bili/BV1xx411c7mT
    """
    from lib.platform_metrics import get_platform_metrics
    
    logger.info(f"📊 Fetching metrics: {platform}/{content_id}")
    
    metrics_client = get_platform_metrics()
    result = await metrics_client.get_metrics(platform, content_id)
    
    return result.to_dict()


@app.get("/perception/platform-metrics/batch")
async def get_platform_metrics_batch(
    platform: str,
    content_ids: str  # Comma-separated
):
    """
    Fetch metrics for multiple pieces of content.
    
    Query params:
        platform: Platform code (bili, dy, xhs, wb)
        content_ids: Comma-separated list of content IDs
        
    Returns:
        Array of metrics for each content ID
    """
    from lib.platform_metrics import get_platform_metrics
    
    ids = [id.strip() for id in content_ids.split(",") if id.strip()]
    
    if not ids:
        return {"success": False, "error": "No content IDs provided"}
    
    if len(ids) > 20:
        return {"success": False, "error": "Maximum 20 IDs per batch"}
    
    metrics_client = get_platform_metrics()
    
    results = []
    for content_id in ids:
        result = await metrics_client.get_metrics(platform, content_id)
        results.append(result.to_dict())
    
    return {
        "success": True,
        "platform": platform,
        "count": len(results),
        "metrics": results
    }


# =============================================
# Perception Feedback Loop Endpoints (Phase 4)
# =============================================

class PerformanceFeedback(BaseModel):
    """Performance metrics for a published topic."""
    actual_views: int = 0
    actual_likes: int = 0
    comments: int = 0
    shares: int = 0
    completion_rate: Optional[float] = None
    measured_at: Optional[str] = None


@app.get("/perception/topics-needing-feedback")
async def get_topics_needing_feedback(
    hours: int = 168,
    limit: int = 50
):
    """
    Find topics that have been published but lack performance metrics.
    
    Called by: N8N workflow 13_Perception_Feedback_Loop
    
    Query params:
        hours: Look back period (default 168 = 7 days)
        limit: Max topics to return
        
    Returns:
        Topics with status='published' but empty performance metrics.
    """
    from lib.sanity_client import get_sanity_client
    from datetime import datetime, timedelta, timezone
    
    client = get_sanity_client()
    
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    
    # Find published topics without performance data
    query = f'''
        *[_type == "topic" && status == "published" && _createdAt >= "{cutoff}"] | order(_createdAt desc) [0...{limit}] {{
            _id,
            title,
            status,
            source_type,
            "performance": performance,
            "artist_name": assigned_artist->name,
            _createdAt
        }}
    '''
    
    topics = client.query(query) or []
    
    # Filter to topics with missing or incomplete performance
    needing_feedback = []
    for topic in topics:
        perf = topic.get("performance", {}) or {}
        # Check if views are missing or zero
        if not perf.get("actual_views"):
            needing_feedback.append(topic)
    
    return {
        "success": True,
        "count": len(needing_feedback),
        "hours": hours,
        "topics": needing_feedback
    }


@app.post("/perception/feedback/{topic_id}")
async def write_topic_feedback(topic_id: str, feedback: PerformanceFeedback):
    """
    Write performance metrics to a topic.
    
    Called by: N8N workflow 13_Perception_Feedback_Loop
    
    Updates the topic.performance fields in Sanity.
    Also calculates performance delta vs predicted if available.
    """
    from lib.sanity_client import get_sanity_client
    from datetime import datetime, timezone
    
    client = get_sanity_client()
    
    # Build performance update
    performance_data = {
        "actual_views": feedback.actual_views,
        "actual_likes": feedback.actual_likes,
        "comments": feedback.comments,
        "shares": feedback.shares,
        "measured_at": feedback.measured_at or datetime.now(timezone.utc).isoformat()
    }
    
    if feedback.completion_rate is not None:
        performance_data["completion_rate"] = feedback.completion_rate
    
    # Patch the topic
    try:
        result = client.patch(topic_id, {"performance": performance_data})
        
        logger.info(f"📊 Wrote feedback for {topic_id}: {feedback.actual_views} views")
        
        return {
            "success": True,
            "topic_id": topic_id,
            "performance": performance_data
        }
    except Exception as e:
        logger.error(f"Failed to write feedback for {topic_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/perception/feedback-stats")
async def get_feedback_stats(hours: int = 168):
    """
    Get aggregated feedback statistics.
    
    Called by: N8N workflow 13_Perception_Feedback_Loop
    
    Returns:
        - Total topics with feedback
        - Average views, likes, completion rate
        - Top performers
    """
    from lib.sanity_client import get_sanity_client
    from datetime import datetime, timedelta, timezone
    
    client = get_sanity_client()
    
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    
    # Get topics with performance data
    query = f'''
        *[_type == "topic" && status == "published" && defined(performance.actual_views) && _createdAt >= "{cutoff}"] | order(performance.actual_views desc) {{
            _id,
            title,
            source_type,
            performance,
            "artist_name": assigned_artist->name
        }}
    '''
    
    topics = client.query(query) or []
    
    if not topics:
        return {
            "success": True,
            "total_with_feedback": 0,
            "avg_views": 0,
            "avg_likes": 0,
            "top_performers": []
        }
    
    # Calculate aggregates
    total_views = sum(t.get("performance", {}).get("actual_views", 0) for t in topics)
    total_likes = sum(t.get("performance", {}).get("actual_likes", 0) for t in topics)
    
    avg_views = total_views / len(topics) if topics else 0
    avg_likes = total_likes / len(topics) if topics else 0
    
    # Top 5 performers
    top_performers = [
        {
            "topic_id": t["_id"],
            "title": t.get("title", "")[:50],
            "views": t.get("performance", {}).get("actual_views", 0),
            "likes": t.get("performance", {}).get("actual_likes", 0)
        }
        for t in topics[:5]
    ]
    
    return {
        "success": True,
        "hours": hours,
        "total_with_feedback": len(topics),
        "avg_views": round(avg_views, 1),
        "avg_likes": round(avg_likes, 1),
        "top_performers": top_performers
    }


# =============================================
# MAB Weight Adjustment Endpoints (Phase 6)
# =============================================

@app.get("/perception/mab/analyze/{artist_id}")
async def mab_analyze_artist(
    artist_id: str,
    lookback_days: int = 30
):
    """
    Analyze artist's topic performance and suggest weight adjustments.
    
    Uses Multi-Armed Bandit approach to correlate topic factors
    (recency, relevance, source, novelty) with performance (views).
    
    Called by: N8N workflow 14_MAB_Weight_Tuning
    
    Path params:
        artist_id: Sanity artist document ID
        
    Query params:
        lookback_days: Days of history to analyze (default 30)
    """
    from lib.mab_agent import get_mab_agent
    
    logger.info(f"🎰 MAB analysis for {artist_id}")
    
    try:
        agent = get_mab_agent()
        result = await agent.analyze_and_adjust(artist_id, auto_apply=False)
        
        return {
            "success": True,
            **result
        }
    except Exception as e:
        logger.error(f"MAB analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/perception/mab/update/{artist_id}")
async def mab_update_weights(
    artist_id: str,
    auto_apply: bool = True
):
    """
    Analyze and apply weight adjustments to artist.
    
    Only applies if confidence > 0.6 (sufficient sample size).
    
    Path params:
        artist_id: Sanity artist document ID
        
    Query params:
        auto_apply: If True (default), apply changes if confident
    """
    from lib.mab_agent import get_mab_agent
    
    logger.info(f"🎰 MAB update for {artist_id}")
    
    try:
        agent = get_mab_agent()
        result = await agent.analyze_and_adjust(artist_id, auto_apply=auto_apply)
        
        return {
            "success": True,
            **result
        }
    except Exception as e:
        logger.error(f"MAB update error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/perception/mab/all-artists")
async def mab_analyze_all_artists():
    """
    Analyze all artists and return aggregated MAB insights.
    
    Useful for weekly dashboard/reporting.
    """
    from lib.sanity_client import get_sanity_client
    from lib.mab_agent import get_mab_agent
    
    sanity = get_sanity_client()
    agent = get_mab_agent()
    
    # Get all active artists
    artists = sanity.query('*[_type == "artist" && !(_id in path("drafts.**"))] { _id, name }') or []
    
    results = []
    for artist in artists[:20]:  # Limit to 20
        try:
            analysis = await agent.analyze_and_adjust(artist["_id"], auto_apply=False)
            results.append({
                "artist_id": artist["_id"],
                "name": artist.get("name", "Unknown"),
                "topics_analyzed": analysis["topics_analyzed"],
                "confidence": analysis["confidence"],
                "top_correlation": max(analysis["correlations"].values()) if analysis["correlations"] else 0
            })
        except Exception as e:
            logger.warning(f"MAB analysis failed for {artist['_id']}: {e}")
    
    return {
        "success": True,
        "artists_analyzed": len(results),
        "results": results
    }


# =============================================
# Super Spike Detection Endpoints (Phase 7)
# =============================================

@app.get("/perception/spike/check/{topic_id}")
async def check_topic_spike(topic_id: str):
    """
    Check if a topic is a Super Spike (velocity >300% baseline).
    
    Path params:
        topic_id: Sanity topic document ID
    """
    from lib.sanity_client import get_sanity_client
    from lib.perception_pipeline import get_perception_pipeline
    
    sanity = get_sanity_client()
    pipeline = get_perception_pipeline()
    
    topic = sanity.query(
        '*[_type == "topic" && _id == $id][0]',
        {"id": topic_id}
    )
    
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    
    niche_id = topic.get("niche", {}).get("_ref")
    
    result = await pipeline.check_super_spike(topic, niche_id)
    
    return {
        "success": True,
        "topic_id": topic_id,
        **result
    }


@app.post("/perception/spike/ingest")
async def ingest_with_spike_detection(req: PerceptionIngestRequest):
    """
    Ingest signal with automatic spike detection.
    
    If velocity exceeds 300% of niche baseline:
    - Sets topic status to 'urgent'
    - Fires webhook to N8N for immediate processing
    """
    from lib.perception_pipeline import get_perception_pipeline
    
    logger.info(f"🔥 Spike-aware ingest: {req.title[:50]}...")
    
    try:
        pipeline = get_perception_pipeline()
        result = await pipeline.process_with_spike_detection(
            title=req.title,
            source_type=req.source_type,
            platform=req.platform,
            content=req.content,
            url=req.url,
            metrics=req.metrics,
            keywords=req.keywords,
            niche_id=req.niche_id
        )
        return result
    except Exception as e:
        logger.error(f"Spike ingest error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/perception/spike/update-baseline/{niche_id}")
async def update_niche_baseline(niche_id: str, lookback_days: int = 30):
    """
    Update velocity baseline for spike detection.
    
    Calculates median velocity from recent topics and updates nicheConfig.
    
    Path params:
        niche_id: Niche config document ID
        
    Query params:
        lookback_days: Days of history to analyze (default 30)
    """
    from lib.perception_pipeline import get_perception_pipeline
    
    pipeline = get_perception_pipeline()
    result = await pipeline.update_niche_baseline(niche_id, lookback_days)
    
    return {
        "success": result.get("success", False),
        **result
    }


# =============================================
# Curriculum DAG Endpoints (Phase 8)
# =============================================

@app.get("/perception/curriculum/available/{artist_id}")
async def get_available_chapters(
    artist_id: str,
    track: str = None
):
    """
    Get chapters available to start (prerequisites satisfied).
    
    Uses DAG logic: chapter is available if ALL prerequisites are completed.
    
    Path params:
        artist_id: Sanity artist document ID
        
    Query params:
        track: Optional filter (core, bonus, advanced)
    """
    from lib.open_notebook_client import get_open_notebook_client
    
    client = get_open_notebook_client()
    chapters = await client.get_available_chapters(artist_id, track)
    
    return {
        "success": True,
        "artist_id": artist_id,
        "available_count": len(chapters),
        "chapters": chapters
    }


@app.post("/perception/curriculum/complete/{chapter_id}")
async def mark_chapter_complete(
    chapter_id: str,
    artist_id: str,
    video_id: str = None
):
    """
    Mark a chapter as completed.
    
    Path params:
        chapter_id: Chapter document ID
        
    Query params:
        artist_id: Artist who completed the chapter
        video_id: Optional video reference
    """
    from lib.open_notebook_client import get_open_notebook_client
    
    client = get_open_notebook_client()
    result = await client.mark_chapter_complete(artist_id, chapter_id, video_id)
    
    return result


@app.get("/perception/curriculum/progress/{artist_id}")
async def get_curriculum_progress(artist_id: str):
    """
    Get DAG-aware progress with track breakdown.
    
    Returns total, completed, available, locked counts plus per-track breakdown.
    """
    from lib.open_notebook_client import get_open_notebook_client
    
    client = get_open_notebook_client()
    result = await client.get_dag_progress(artist_id)
    
    return {
        "success": True,
        **result
    }


@app.post("/perception/curriculum/validate")
async def validate_curriculum():
    """
    Validate curriculum DAG for cycles.
    
    Uses graphlib TopologicalSorter to detect invalid dependencies.
    Should be called after curriculum edits.
    """
    from graphlib import TopologicalSorter, CycleError
    from lib.sanity_client import get_sanity_client
    
    sanity = get_sanity_client()
    
    # Get all chapters with prerequisites
    chapters = sanity.query('''
        *[_type == "chapter"] {
            _id,
            title,
            "prereqs": prerequisites[]._ref
        }
    ''') or []
    
    # Build graph for TopologicalSorter
    graph = {}
    for ch in chapters:
        graph[ch["_id"]] = set(ch.get("prereqs") or [])
    
    try:
        ts = TopologicalSorter(graph)
        ts.prepare()  # This checks for cycles
        
        return {
            "success": True,
            "valid": True,
            "chapters_count": len(chapters),
            "message": "Curriculum DAG is valid (no cycles)"
        }
        
    except CycleError as e:
        cycle = e.args[1] if len(e.args) > 1 else []
        
        return {
            "success": True,
            "valid": False,
            "chapters_count": len(chapters),
            "message": f"Cycle detected: {' -> '.join(cycle)}"
        }


# =============================================
# IR Normalizer Endpoints (Phase 10)
# =============================================

class IRNormalizeRequest(BaseModel):
    """Request for normalizing research output to UCS."""
    source: str  # bettafish, mirothinker, open_notebook
    data: Dict[str, Any]
    source_type: Optional[str] = None  # social, rss, knowledge_base


@app.post("/perception/normalize-ir")
async def normalize_ir_to_ucs(request: IRNormalizeRequest):
    """
    Normalize research output to Universal Context Schema (UCS).
    
    Supports:
    - bettafish: CCO block-based format
    - mirothinker: Deep research report
    - open_notebook: RAG answer with sources
    
    Returns:
        UCS format with core_event, sentiment, analysis, references
    """
    from lib.ir_normalizer import get_ir_normalizer
    
    normalizer = get_ir_normalizer()
    source_type = request.source_type or "social"
    
    try:
        if request.source == "bettafish":
            result = normalizer.normalize_bettafish_ir(request.data, source_type)
        elif request.source == "mirothinker":
            result = normalizer.normalize_mirothinker_report(request.data, source_type)
        elif request.source == "open_notebook":
            result = normalizer.normalize_opennotebook_rag(request.data, source_type)
        else:
            raise HTTPException(400, f"Unknown source: {request.source}")
        
        return {
            "success": True,
            "ucs": result
        }
    except Exception as e:
        logger.error(f"IR normalization error: {e}")
        raise HTTPException(500, str(e))


# =============================================
# Artist Matching Endpoints (Phase 5)
# =============================================

@app.post("/perception/match/{topic_id}")
async def match_topic_to_artist(
    topic_id: str,
    auto_assign: bool = True
):
    """
    Match a topic to the best artist using funnel strategy.
    
    Deep Think Funnel Strategy:
    1. Hard Filter - Niche match, exclude keywords
    2. Soft Rank - Embedding similarity (topic ↔ artist backstory)
    3. Load Balance - Penalty for artists with pending topics
    
    Path params:
        topic_id: Sanity topic document ID
        
    Query params:
        auto_assign: If True, automatically assign artist to topic
    """
    from lib.artist_matcher import get_artist_matcher
    
    logger.info(f"🎯 Matching topic: {topic_id}")
    
    try:
        matcher = get_artist_matcher()
        result = await matcher.match_topic(topic_id, auto_assign)
        return result
    except Exception as e:
        logger.error(f"Match error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/perception/batch-match")
async def batch_match_topics(
    status: str = "new",
    limit: int = 10
):
    """
    Match multiple unassigned topics in batch.
    
    Processes topics ordered by z_score_velocity (hottest first).
    
    Query params:
        status: Only match topics with this status (default: new)
        limit: Max topics to process (default: 10)
    """
    from lib.artist_matcher import get_artist_matcher
    
    logger.info(f"📋 Batch matching: status={status}, limit={limit}")
    
    try:
        matcher = get_artist_matcher()
        result = await matcher.batch_match(status, limit)
        return result
    except Exception as e:
        logger.error(f"Batch match error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/perception/artists-by-niche")
async def get_artists_by_niche(niche: str):
    """
    Get artists available for a niche category.
    
    Query params:
        niche: Niche category (finance, tech, kids, metaphysics)
    """
    from lib.sanity_client import get_sanity_client
    
    client = get_sanity_client()
    artists = client.get_artists_by_niche_category(niche)
    
    return {
        "success": True,
        "niche": niche,
        "count": len(artists),
        "artists": artists
    }


# =============================================
# Feedback Loop Endpoints (Phase 6)
# =============================================

class PerformanceFeedback(BaseModel):
    """Feedback data for post-publish performance."""
    actual_views: int
    actual_likes: int = 0
    measured_at: Optional[str] = None  # ISO datetime


@app.post("/perception/feedback/{topic_id}")
async def write_performance_feedback(
    topic_id: str,
    feedback: PerformanceFeedback
):
    """
    Write back actual performance metrics to a topic.
    
    Called after a topic's generated post is published and metrics are available.
    Updates the topic's performance field and calculates accuracy ratio.
    
    Path params:
        topic_id: Sanity topic document ID
        
    Body:
        actual_views: Actual view count from platform
        actual_likes: Actual like count
        measured_at: When metrics were captured (ISO datetime)
    """
    from lib.sanity_client import get_sanity_client
    from datetime import datetime, timezone
    
    client = get_sanity_client()
    
    # Get topic with predicted metrics
    topic = client.query(
        '*[_type == "topic" && _id == $id][0] { z_score_velocity, signals }',
        {"id": topic_id}
    )
    
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    
    # Calculate accuracy ratio (predicted vs actual)
    predicted_velocity = topic.get("z_score_velocity") or 0
    signals = topic.get("signals") or []
    predicted_engagement = sum(
        (s.get("metrics", {}).get("likes", 0) or 0) + 
        (s.get("metrics", {}).get("comments", 0) or 0)
        for s in signals
    )
    
    # Calculate accuracy (0-1 scale, based on how close prediction was)
    if predicted_engagement > 0:
        accuracy = min(feedback.actual_views / (predicted_engagement * 10), 2.0) / 2.0
    else:
        accuracy = 0.5  # No prediction to compare
    
    # Update topic performance
    measured_at = feedback.measured_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    
    client.patch(topic_id, {
        "performance": {
            "actual_views": feedback.actual_views,
            "actual_likes": feedback.actual_likes,
            "measured_at": measured_at,
            "accuracy_ratio": round(accuracy, 2)
        }
    })
    
    logger.info(f"📊 Feedback recorded: topic={topic_id}, views={feedback.actual_views}, accuracy={accuracy:.2f}")
    
    return {
        "success": True,
        "topic_id": topic_id,
        "accuracy_ratio": round(accuracy, 2),
        "feedback_recorded": True
    }


@app.get("/perception/topics-needing-feedback")
async def get_topics_needing_feedback(limit: int = 20):
    """
    Get topics with generated posts that don't have performance feedback yet.
    
    Used by n8n workflow to identify which posts need metrics collection.
    """
    from lib.sanity_client import get_sanity_client
    
    client = get_sanity_client()
    
    # Simple query without GROQ parameter interpolation
    topics = client.query(
        '''*[_type == "topic" && 
            defined(generated_post) && 
            !defined(performance.actual_views)
        ] | order(_createdAt desc) [0...50] {
            _id,
            title,
            "post_id": generated_post._ref,
            _createdAt,
            "artist_name": assigned_artist->name
        }'''
    )
    
    # Apply limit in Python
    topics = (topics or [])[:limit]
    
    return {
        "success": True,
        "count": len(topics),
        "topics": topics
    }


@app.get("/perception/feedback-stats")
async def get_feedback_stats():
    """
    Get aggregate feedback loop statistics.
    
    Returns average accuracy, best/worst performing topics, etc.
    """
    from lib.sanity_client import get_sanity_client
    
    client = get_sanity_client()
    
    stats = client.query('''
        {
            "total_topics": count(*[_type == "topic"]),
            "with_feedback": count(*[_type == "topic" && defined(performance.actual_views)]),
            "avg_accuracy": math::avg(*[_type == "topic" && defined(performance.accuracy_ratio)].performance.accuracy_ratio),
            "avg_views": math::avg(*[_type == "topic" && defined(performance.actual_views)].performance.actual_views),
            "top_performers": *[_type == "topic" && defined(performance.actual_views)] | order(performance.actual_views desc) [0...3] {
                _id, title, "views": performance.actual_views
            }
        }
    ''')
    
    return {
        "success": True,
        "stats": stats
    }


# =============================================
# Knowledge Base Endpoints (open-notebook)
# =============================================

@app.get("/perception/knowledge/status")
async def knowledge_status():
    """Check if open-notebook is available."""
    from lib.open_notebook_client import get_open_notebook_client
    
    client = get_open_notebook_client()
    
    return {
        "available": client.is_available(),
        "url": client.base_url
    }


@app.get("/perception/knowledge/notebooks")
async def list_knowledge_notebooks():
    """List all notebooks in open-notebook."""
    from lib.open_notebook_client import get_open_notebook_client
    
    client = get_open_notebook_client()
    notebooks = await client.list_notebooks()
    
    return {
        "success": True,
        "count": len(notebooks),
        "notebooks": notebooks
    }


@app.get("/perception/knowledge/sources/{notebook_id}")
async def list_notebook_sources(notebook_id: str):
    """List all sources in a notebook."""
    from lib.open_notebook_client import get_open_notebook_client
    
    client = get_open_notebook_client()
    sources = await client.list_sources(notebook_id)
    
    return {
        "success": True,
        "notebook_id": notebook_id,
        "count": len(sources),
        "sources": sources
    }


class KnowledgeGenerateRequest(BaseModel):
    """Request for generating topics from notebook."""
    count: int = 5
    style: str = "social_media"
    niche_id: Optional[str] = None


@app.post("/perception/knowledge/generate/{notebook_id}")
async def generate_topics_from_knowledge(
    notebook_id: str,
    req: KnowledgeGenerateRequest
):
    """
    Generate topics from notebook knowledge using RAG.
    
    Uses open-notebook to extract topic ideas from curated documents,
    then creates topics in Sanity through the perception pipeline.
    
    Path params:
        notebook_id: open-notebook notebook ID
        
    Body:
        count: Number of topics to generate
        style: Content style (social_media, educational, news)
        niche_id: Optional niche to associate topics with
    """
    from lib.open_notebook_client import get_open_notebook_client
    from lib.perception_pipeline import get_perception_pipeline
    
    logger.info(f"📚 Generating {req.count} topics from notebook: {notebook_id}")
    
    try:
        # Get topics from open-notebook
        client = get_open_notebook_client()
        raw_topics = await client.generate_topics(notebook_id, req.count, req.style)
        
        if not raw_topics:
            return {
                "success": False,
                "error": "No topics generated from notebook"
            }
        
        # Create topics in perception pipeline
        pipeline = get_perception_pipeline()
        topics_created = 0
        
        for topic_data in raw_topics:
            try:
                result = await pipeline.ingest_signal(
                    title=topic_data.get("title", "Untitled"),
                    source_type="knowledge_base",
                    platform="open-notebook",
                    content=str(topic_data.get("key_points", [])),
                    keywords=[],
                    niche_id=req.niche_id
                )
                if result.get("success"):
                    topics_created += 1
            except Exception as e:
                logger.error(f"Error creating topic: {e}")
        
        return {
            "success": True,
            "notebook_id": notebook_id,
            "topics_generated": len(raw_topics),
            "topics_created": topics_created
        }
        
    except Exception as e:
        logger.error(f"Knowledge generate error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== BettaFish Full Analysis Pipeline ====================

class FullAnalysisRequest(BaseModel):
    """Request for full BettaFish analysis pipeline."""
    query: str  # e.g., "小牛电动车品牌分析"
    generate_pdf: bool = False  # Whether to generate PDF report
    parallel: bool = True  # Run engines in parallel (recommended)
    max_rounds: int = 1  # Forum discussion rounds
    crawl_first: bool = False  # Run MediaCrawlerPro before analysis
    platforms: Optional[List[str]] = None  # Platforms to crawl: xhs, weibo, douyin, bilibili
    skip_report: bool = False  # Skip ReportEngine final report generation (faster, avoids blocking)


@app.post("/bettafish/full-analysis")
async def run_full_bettafish_analysis(req: FullAnalysisRequest):
    """
    Run complete BettaFish analysis pipeline.
    
    This replicates the BettaFish Streamlit UI workflow:
    0. (Optional) Crawl fresh data via MediaCrawlerPro
    1. Run all 3 engines in parallel (Insight, Media, Query)
    2. ForumEngine synthesizes findings with conflict detection
    3. Save engine reports to BettaFish directories
    4. Generate comprehensive HTML/PDF report via ReportEngine
    
    Usage:
        POST /bettafish/full-analysis
        {
            "query": "特朗普",
            "crawl_first": true,
            "platforms": ["xhs", "weibo"],
            "generate_pdf": false,
            "parallel": true,
            "max_rounds": 1
        }
    
    Returns:
        - crawl_results: Results of pre-crawl (if crawl_first=true)
        - engine_reports: Paths to individual engine reports
        - final_report: Path to generated HTML/PDF report
        - forum_synthesis: LLM host analysis summary
        - execution_time_seconds: Total processing time
    
    Note: This is a long-running operation (~10-30 minutes for deep analysis).
    With crawl_first=true, add ~5 minutes per platform.
    Consider setting appropriate timeout in your HTTP client.
    """
    from lib.forum_engine import get_forum_engine
    import asyncio
    
    crawl_msg = " (with pre-crawl)" if req.crawl_first else ""
    logger.info(f"🎯 Starting full BettaFish analysis{crawl_msg}: {req.query}")
    
    # Get forum engine (handles all 3 engines + synthesis)
    fe = get_forum_engine()
    
    # Run the full analysis (this is a blocking operation)
    # Use run_in_executor to not block the event loop
    loop = asyncio.get_event_loop()
    
    try:
        result = await loop.run_in_executor(
            None,
            lambda: fe.run_full_analysis(
                query=req.query,
                generate_pdf=req.generate_pdf,
                parallel=req.parallel,
                max_rounds=req.max_rounds,
                crawl_first=req.crawl_first,
                platforms=req.platforms,
                skip_report=req.skip_report
            )
        )
        
        if result.get("success"):
            logger.info(f"✅ Full analysis complete: {result.get('execution_time_seconds')}s")
        else:
            logger.warning(f"⚠️ Analysis had issues: {result.get('error')}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Full analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class BroadTopicRequest(BaseModel):
    """Request for broad topic extraction."""
    max_keywords: int = 20


@app.post("/bettafish/broad-topic-extraction")
async def run_broad_topic_extraction(req: BroadTopicRequest):
    """
    Run MindSpider BroadTopicExtraction to collect trending topics.
    
    This crawls 12 news/social platforms and extracts hot keywords.
    Use this endpoint from N8N scheduled workflows.
    
    Returns:
        - success: bool
        - topics_count: number of topics found
        - output: command output (last 30 lines)
    """
    import subprocess
    from pathlib import Path
    import asyncio
    
    logger.info(f"🕷️ Running BroadTopicExtraction (max_keywords={req.max_keywords})")
    
    mindspider_path = Path("/home/jimmy/Documents/mcn/external/BettaFish/MindSpider")
    venv_python = mindspider_path.parent / ".venv/bin/python"
    
    loop = asyncio.get_event_loop()
    
    try:
        def run_extraction():
            cmd = [
                str(venv_python),
                "main.py",
                "--broad-topic",
                "--keywords", str(req.max_keywords)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                cwd=str(mindspider_path)
            )
            
            return result
        
        result = await loop.run_in_executor(None, run_extraction)
        
        # Get last 30 lines of output
        output_lines = (result.stdout + result.stderr).strip().split('\n')[-30:]
        
        if result.returncode == 0:
            logger.info("✅ BroadTopicExtraction complete")
            return {
                "success": True,
                "topics_count": req.max_keywords,
                "output": '\n'.join(output_lines)
            }
        else:
            logger.warning(f"⚠️ BroadTopicExtraction exited with code {result.returncode}")
            return {
                "success": False,
                "error": result.stderr[:500] if result.stderr else "Unknown error",
                "output": '\n'.join(output_lines)
            }
            
    except subprocess.TimeoutExpired:
        logger.error("❌ BroadTopicExtraction timed out")
        return {"success": False, "error": "Timeout (5 min limit)"}
    except Exception as e:
        logger.error(f"❌ BroadTopicExtraction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/bettafish/full-analysis/status")
async def get_full_analysis_status():
    """
    Check status of BettaFish full analysis components.
    
    Verifies:
    - InsightEngine availability
    - MediaEngine availability (Bocha)
    - QueryEngine availability (Tavily)
    - ForumEngine availability
    - ReportEngine availability
    """
    from lib.forum_engine import get_forum_engine
    import os
    from pathlib import Path
    
    bettafish_path = Path("/home/jimmy/Documents/mcn/external/BettaFish")
    
    status = {
        "insight_engine": {
            "available": True,
            "type": "BettaFish KeywordOptimizer + DB"
        },
        "media_engine": {
            "available": os.getenv("BOCHA_API_KEY") is not None,
            "type": "Bocha AI Multimodal Search"
        },
        "query_engine": {
            "available": os.getenv("TAVILY_API_KEY") is not None,
            "type": "Tavily Web/News Search"
        },
        "forum_engine": {
            "available": True,
            "type": "LLM Host (via Antigravity Manager)"
        },
        "report_engine": {
            "available": (bettafish_path / "report_engine_only.py").exists(),
            "type": "BettaFish ReportEngine"
        },
        "report_directories": {
            "insight": str(bettafish_path / "insight_engine_streamlit_reports"),
            "media": str(bettafish_path / "media_engine_streamlit_reports"),
            "query": str(bettafish_path / "query_engine_streamlit_reports"),
            "final": str(bettafish_path / "final_reports")
        }
    }
    
    # Overall status
    all_available = all([
        status["insight_engine"]["available"],
        status["query_engine"]["available"],
        status["forum_engine"]["available"],
        status["report_engine"]["available"]
    ])
    
    return {
        "ready": all_available,
        "components": status,
        "note": "See /docs for API documentation"
    }


# =============================================
# Flow 1: Social Crawler Orchestration
# =============================================
from lib.flow1_orchestrator import get_flow1_orchestrator


class Flow1ApproveTopicRequest(BaseModel):
    """Request body for approving a topic."""
    topic_id: Optional[str] = None  # Use if topic already exists in Sanity
    candidate: Optional[Dict[str, Any]] = None  # Use if creating from candidate
    niche_id: Optional[str] = None  # Required if using candidate


class Flow1RejectRequest(BaseModel):
    """Request body for rejecting topic or script."""
    reason: Optional[str] = None


class Flow1GenerateScriptRequest(BaseModel):
    """Request body for script generation."""
    artist_id: str
    duration_seconds: int = 60


class Flow1RetryWithAngleRequest(BaseModel):
    """Request body for retrying planning with adjusted angle."""
    adjusted_angle: str
    persona_threshold: float = 0.7


@app.get("/flow1/config")
async def flow1_get_config():
    """
    Get Flow 1 configuration including test mode status.

    Returns:
        {
            "test_mode": True/False,
            "schedule_timezone": "Asia/Shanghai",
            "env_vars": {...}
        }
    """
    return {
        "success": True,
        "test_mode": FLOW1_TEST_MODE,
        "schedule_timezone": os.getenv("SCHEDULE_TIMEZONE", "Asia/Shanghai"),
        "env_vars": {
            "FLOW1_TEST_MODE": os.getenv("FLOW1_TEST_MODE", "false"),
            "SCHEDULE_TIMEZONE": os.getenv("SCHEDULE_TIMEZONE", "Asia/Shanghai")
        },
        "usage": {
            "enable_test_mode": "Set FLOW1_TEST_MODE=true in .env",
            "test_any_artist": "POST /flow1/test-trigger/{artist_id}",
            "list_testable_artists": "GET /flow1/test-artists"
        }
    }


@app.get("/flow1/due-schedules")
async def flow1_get_due_schedules(test_mode: bool = None):
    """
    Get schedules that should execute now based on their routine_config.

    N8N should poll this endpoint every 5 minutes to check for due schedules.

    Args:
        test_mode: Override test mode (if True, returns ALL social artists regardless of schedule)

    Returns schedules where:
    - active == true
    - type == "routine"
    - Current day matches routine_config.days (weekly) or month_days (monthly)
    - Current time is within 10 minutes of routine_config.times
    - last_executed is not within the current time window

    Each returned schedule includes:
    - schedule_id: For marking as executed
    - artist: {_id, name} - The artist to generate content for
    - niche: {_id, name, coreKeywords, platforms} - The artist's niche config

    Returns:
        {"success": True, "due_schedules": [...], "checked_at": "..."}
    """
    # Use parameter or env var for test mode
    is_test_mode = test_mode if test_mode is not None else FLOW1_TEST_MODE

    if is_test_mode:
        # In test mode, return all social artists as "due"
        from lib.sanity_client import get_sanity_client
        sanity = get_sanity_client()

        artists = sanity.query('''
            *[_type == "artist" && primaryFlowType == "social" && defined(nicheConfig)]{
                _id,
                name,
                "nicheConfig": nicheConfig->{
                    _id,
                    name,
                    coreKeywords,
                    platforms
                }
            }
        ''') or []

        due_schedules = []
        for artist in artists:
            niche = artist.get("nicheConfig")
            if niche:
                due_schedules.append({
                    "schedule_id": f"test-{artist.get('_id')}",
                    "schedule_title": f"[TEST] {artist.get('name')}",
                    "artist": {
                        "_id": artist.get("_id"),
                        "name": artist.get("name")
                    },
                    "niche": niche,
                    "test_mode": True
                })

        from datetime import datetime, timezone
        return {
            "success": True,
            "test_mode": True,
            "due_schedules": due_schedules,
            "total_checked": len(artists),
            "checked_at": datetime.now(timezone.utc).isoformat()
        }

    # Normal mode - check actual schedules
    orchestrator = get_flow1_orchestrator()
    return await orchestrator.get_due_schedules()


@app.post("/flow1/mark-executed/{schedule_id}")
async def flow1_mark_schedule_executed(schedule_id: str):
    """
    Mark a schedule as executed to prevent re-triggering.
    
    N8N should call this after successfully processing a schedule.
    Updates the schedule's last_executed timestamp.
    
    Args:
        schedule_id: Sanity schedule document ID
        
    Returns:
        {"success": True, "schedule_id": "...", "last_executed": "..."}
    """
    orchestrator = get_flow1_orchestrator()
    return await orchestrator.mark_schedule_executed(schedule_id)


@app.post("/flow1/trigger-crawl/{niche_id}")
async def flow1_trigger_crawl(
    niche_id: str, 
    wait: bool = True,
    max_wait: int = 120
):
    """
    Step 1: Trigger MindSpider/MediaCrawler for fresh data.
    
    This initiates the social crawl for a specific niche configuration.
    The crawl will collect hot topics from configured platforms.
    
    By default (wait=True), this endpoint will wait until topics appear in MySQL
    before returning. Set wait=False for async background crawl.
    
    Args:
        niche_id: Sanity niche config document ID
        wait: If True, wait for crawl to produce results (default True)
        max_wait: Maximum seconds to wait for results (default 120)
        
    Returns:
        {"success": True, "stats": {...}, "topics_found": N}
    """
    orchestrator = get_flow1_orchestrator()
    result = await orchestrator.run_scheduled_crawl(
        niche_id, 
        wait_for_results=wait,
        max_wait_seconds=max_wait
    )
    return result


@app.post("/flow1/trigger-homefeed/{niche_id}")
async def flow1_trigger_homefeed(
    niche_id: str,
    wait: bool = False,
    max_wait: int = 120
):
    """
    Trigger HomeFeed crawl for a niche using trained accounts.
    
    HomeFeed mode crawls the personalized recommendation feed of accounts
    that have been trained by browsing niche-specific content.
    
    Requires crawlerAccount documents in Sanity with:
    - crawlerType: "homefeed"
    - niche: reference to the target nicheConfig
    
    Args:
        niche_id: Sanity niche config document ID
        wait: If True, wait for crawl to produce results (default False)
        max_wait: Maximum seconds to wait for results (default 120)
        
    Returns:
        {"success": True, "platforms_crawled": [...], "crawl_stats": {...}}
    """
    orchestrator = get_flow1_orchestrator()
    result = await orchestrator.perception.crawl_niche_homefeed(
        niche_id,
        wait_for_results=wait,
        max_wait_seconds=max_wait
    )
    return result


@app.get("/flow1/candidates/{niche_id}")
async def flow1_get_candidates(
    niche_id: str,
    page: int = 1,
    per_page: int = 3,
    time_period: str = "week"
):
    """
    Step 2: Get velocity-scored hot topics for human review.
    
    Returns paginated topic candidates sorted by hotness score.
    Supports "Request more topics" via pagination.
    
    Args:
        niche_id: Sanity niche config document ID
        page: Page number (1-indexed)
        per_page: Topics per page (default 3)
        time_period: 24h, week, or year
        
    Returns:
        {"topics": [...], "page": 1, "has_more": True}
    """
    orchestrator = get_flow1_orchestrator()
    result = await orchestrator.get_topic_candidates(
        niche_id=niche_id,
        limit=per_page,
        page=page,
        time_period=time_period
    )
    return result


@app.post("/flow1/approve-topic/{topic_id}")
async def flow1_approve_topic_by_id(topic_id: str):
    """
    Step 3a: Approve an existing topic for deep analysis.
    
    Use this when the topic already exists in Sanity.
    
    Args:
        topic_id: Sanity topic document ID
        
    Returns:
        {"success": True, "status": "analyzing"}
    """
    orchestrator = get_flow1_orchestrator()
    result = await orchestrator.approve_topic(topic_id=topic_id)
    return result


@app.post("/flow1/approve-topic")
async def flow1_approve_topic(req: Flow1ApproveTopicRequest):
    """
    Step 3b: Approve a topic (by ID or create from candidate).
    
    Either:
    - Provide topic_id to approve existing topic
    - Provide candidate + niche_id to create new topic from candidate
    
    Returns:
        {"success": True, "topic_id": "...", "status": "analyzing"}
    """
    orchestrator = get_flow1_orchestrator()
    result = await orchestrator.approve_topic(
        topic_id=req.topic_id,
        candidate=req.candidate,
        niche_id=req.niche_id
    )
    return result


@app.post("/flow1/reject-topic/{topic_id}")
async def flow1_reject_topic(topic_id: str, req: Flow1RejectRequest):
    """
    Reject a topic from consideration.
    
    Args:
        topic_id: Sanity topic document ID
        reason: Optional rejection reason
        
    Returns:
        {"success": True, "status": "rejected"}
    """
    orchestrator = get_flow1_orchestrator()
    result = await orchestrator.reject_topic(topic_id, reason=req.reason)
    return result


@app.post("/flow1/run-analysis/{topic_id}")
async def flow1_run_analysis(topic_id: str, parallel: bool = True, max_rounds: int = 1):
    """
    Step 4: Run full BettaFish deep analysis.
    
    This is a long-running operation (~10-30 minutes).
    Triggers InsightEngine, MediaEngine, QueryEngine, ForumEngine, and ReportEngine.
    
    Args:
        topic_id: Topic ID (must be in 'analyzing' status)
        parallel: Run engines in parallel (recommended)
        max_rounds: Forum discussion rounds
        
    Returns:
        {"success": True, "ir_path": "...", "html_path": "...", "status": "ir_ready"}
    """
    orchestrator = get_flow1_orchestrator()
    result = await orchestrator.run_deep_analysis(
        topic_id=topic_id,
        parallel=parallel,
        max_rounds=max_rounds
    )
    return result


@app.get("/flow1/analysis-status/{topic_id}")
async def flow1_analysis_status(topic_id: str):
    """
    Check analysis progress for a topic.

    Returns:
        {"status": "analyzing" | "ir_ready" | "failed", "analysis_job": {...}}
    """
    orchestrator = get_flow1_orchestrator()
    return orchestrator.get_analysis_status(topic_id)


# =========================================================================
# Step 4.5: Planning Session (策划会)
# =========================================================================

@app.post("/flow1/run-planning/{topic_id}")
async def flow1_run_planning(topic_id: str, persona_threshold: float = 0.7):
    """
    Step 4.5: Run creative planning session after BettaFish analysis.

    Transforms objective research into a creative brief optimized for
    the artist's persona. Includes a hard gate check for persona alignment.

    Args:
        topic_id: Topic ID (must be in 'ir_ready' status)
        persona_threshold: Minimum alignment score (default 0.7)

    Returns:
        {
            "success": True,
            "gate_passed": True/False,
            "status": "brief_ready" | "persona_rejected",
            "creative_brief": {...} or None,
            "persona_rejection": {...} or None
        }
    """
    orchestrator = get_flow1_orchestrator()
    result = await orchestrator.run_planning_session(
        topic_id=topic_id,
        persona_threshold=persona_threshold
    )
    return result


@app.get("/flow1/planning-status/{topic_id}")
async def flow1_planning_status(topic_id: str):
    """
    Check planning session status for a topic.

    Returns:
        {
            "status": "ir_ready" | "brief_ready" | "persona_rejected",
            "planning_job": {...},
            "creative_brief": {...} or None,
            "persona_rejection": {...} or None
        }
    """
    orchestrator = get_flow1_orchestrator()
    return orchestrator.get_planning_status(topic_id)


@app.post("/flow1/retry-with-angle/{topic_id}")
async def flow1_retry_with_angle(topic_id: str, req: Flow1RetryWithAngleRequest):
    """
    Retry planning session with an adjusted angle after gate failure.

    Use this when a topic was rejected due to persona misalignment.
    The adjusted angle should address the concerns raised in the
    persona_rejection.angle_suggestion.

    Args:
        topic_id: Topic ID (must be in 'persona_rejected' status)
        adjusted_angle: New angle to try
        persona_threshold: Minimum alignment score (default 0.7)

    Returns:
        Same as run-planning endpoint
    """
    orchestrator = get_flow1_orchestrator()
    result = await orchestrator.retry_planning_with_angle(
        topic_id=topic_id,
        adjusted_angle=req.adjusted_angle,
        persona_threshold=req.persona_threshold
    )
    return result


@app.post("/flow1/generate-script/{topic_id}")
async def flow1_generate_script(topic_id: str, req: Flow1GenerateScriptRequest):
    """
    Step 5: Generate video script from IR report using Gemini.
    
    Args:
        topic_id: Topic ID (must be in 'ir_ready' status)
        artist_id: Artist ID for persona styling
        duration_seconds: Target video length
        
    Returns:
        {"success": True, "script": [...], "scene_count": N, "status": "scripted"}
    """
    orchestrator = get_flow1_orchestrator()
    result = await orchestrator.generate_script(
        topic_id=topic_id,
        artist_id=req.artist_id,
        duration_seconds=req.duration_seconds
    )
    return result


@app.post("/flow1/approve-script/{topic_id}")
async def flow1_approve_script(topic_id: str):
    """
    Step 6: Approve script, marking topic ready for production.
    
    Args:
        topic_id: Topic ID (must be in 'scripted' status)
        
    Returns:
        {"success": True, "status": "approved"}
    """
    orchestrator = get_flow1_orchestrator()
    result = await orchestrator.approve_script(topic_id)
    return result


@app.post("/flow1/reject-script/{topic_id}")
async def flow1_reject_script(topic_id: str, req: Flow1RejectRequest):
    """
    Reject script, reset to ir_ready for regeneration.
    
    Args:
        topic_id: Topic ID
        reason: Rejection reason
        
    Returns:
        {"success": True, "status": "ir_ready"}
    """
    orchestrator = get_flow1_orchestrator()
    result = await orchestrator.reject_script(topic_id, reason=req.reason)
    return result


@app.post("/flow1/generate-broll/{topic_id}")
async def flow1_generate_broll(topic_id: str, background: bool = True):
    """
    Step 7: Generate B-roll videos from production manifest.

    Reads productionManifest from topic, generates I2V/T2V videos using
    ComfyUI LTX2 workflows, and updates topic with generated video paths.

    Args:
        topic_id: Topic ID (must have productionManifest)
        background: Run async in background (default True)

    Returns:
        If background=True: {"success": True, "task_id": "...", "status": "queued"}
        If background=False: {"success": True, "generated_count": N, ...}
    """
    from lib.sanity_client import get_sanity_client

    sanity = get_sanity_client()

    # Validate topic exists and has production manifest
    topic = sanity.query(
        '*[_id == $id][0]{_id, title, productionManifest, status}',
        {"id": topic_id}
    )

    if not topic:
        raise HTTPException(status_code=404, detail=f"Topic {topic_id} not found")

    if not topic.get("productionManifest"):
        raise HTTPException(
            status_code=400,
            detail=f"Topic {topic_id} has no productionManifest. Run media selection first."
        )

    if background:
        # Queue async task for worker
        task_id = redis_client.enqueue_task(
            "broll_generation",
            {"topic_id": topic_id},
            priority=50  # Medium-high priority
        )
        return {
            "success": True,
            "task_id": task_id,
            "status": "queued",
            "message": f"B-roll generation queued for {topic.get('title', topic_id)}"
        }
    else:
        # Run synchronously (for testing)
        from lib.broll_generator import BRollGenerator
        generator = BRollGenerator()
        result = await generator.generate_from_manifest(topic_id)
        return {"success": True, **result}


@app.get("/flow1/broll-status/{topic_id}")
async def flow1_broll_status(topic_id: str):
    """
    Get B-roll generation status for a topic.

    Returns:
        {"brollStatus": "pending|generating|complete|failed", "generatedBroll": [...]}
    """
    from lib.sanity_client import get_sanity_client

    sanity = get_sanity_client()
    topic = sanity.query(
        '*[_id == $id][0]{_id, title, brollStatus, generatedBroll, productionManifest}',
        {"id": topic_id}
    )

    if not topic:
        raise HTTPException(status_code=404, detail=f"Topic {topic_id} not found")

    manifest = topic.get("productionManifest") or {}
    expected_count = len(manifest.get("i2v_generations", [])) + len(manifest.get("t2v_generations", []))
    generated = topic.get("generatedBroll") or []

    return {
        "success": True,
        "topic_id": topic_id,
        "title": topic.get("title"),
        "brollStatus": topic.get("brollStatus", "pending"),
        "expected_count": expected_count,
        "generated_count": len(generated),
        "generatedBroll": generated
    }


@app.get("/flow1/status/{topic_id}")
async def flow1_get_status(topic_id: str):
    """
    Get complete flow status for a topic.

    Returns:
        {"status": "...", "next_action": "...", "has_ir": True, "has_script": True, ...}
    """
    orchestrator = get_flow1_orchestrator()
    return orchestrator.get_flow_status(topic_id)


@app.get("/flow1/topics/{status}")
async def flow1_get_topics_by_status(status: str, niche_id: Optional[str] = None, limit: int = 20):
    """
    Get all topics in a specific status.
    
    Args:
        status: Topic status (new, pending_review, analyzing, ir_ready, scripted, approved, rejected, failed)
        niche_id: Optional niche filter
        limit: Max results
        
    Returns:
        {"topics": [...]}
    """
    from lib.sanity_client import get_sanity_client
    sanity = get_sanity_client()
    topics = sanity.get_topics_by_status(status, niche_id=niche_id, limit=limit)
    return {"success": True, "status": status, "count": len(topics), "topics": topics}


# ==================== Slack Integration for Topic Review ====================

class SlackTopicReviewRequest(BaseModel):
    """Request to format Slack topic review message."""
    artist_name: str
    topics: List[Dict]
    schedule_id: str
    niche_id: str
    page: int = 1


class SlackActionRequest(BaseModel):
    """Parsed Slack button action."""
    action: str  # pick, more, skip
    schedule_id: str
    niche_id: str
    topic: Optional[Dict] = None
    index: Optional[int] = None
    page: Optional[int] = None


@app.post("/flow1/format-slack-message")
async def flow1_format_slack_message(req: SlackTopicReviewRequest):
    """
    Format topic candidates as Slack Block Kit message for n8n.

    n8n workflow calls this to get the formatted message payload,
    then sends it via the Slack node.

    Args:
        artist_name: Name of the AI artist
        topics: List of topic candidates
        schedule_id: Schedule document ID for tracking
        niche_id: Niche config ID
        page: Current page number

    Returns:
        {"success": True, "slack_message": {...}}
    """
    from lib.slack_notifier import SlackNotifier
    import json

    # Cache topics in Redis for quick retrieval when button is clicked
    # Key format: slack_topics:{niche_id}:{page}
    cache_key = f"slack_topics:{req.niche_id}:{req.page}"
    try:
        redis_client.setex(
            cache_key,
            3600,  # 1 hour TTL
            json.dumps(req.topics)
        )
    except Exception as e:
        logger.warning(f"Failed to cache topics in Redis: {e}")

    notifier = SlackNotifier()
    message = notifier.format_topic_review_blocks(
        artist_name=req.artist_name,
        topics=req.topics,
        schedule_id=req.schedule_id,
        niche_id=req.niche_id,
        page=req.page
    )

    return {"success": True, "slack_message": message}


@app.post("/flow1/slack-action")
async def flow1_handle_slack_action(req: SlackActionRequest):
    """
    Handle Slack button click action from n8n.
    
    n8n receives the Slack interaction webhook and calls this endpoint
    with the parsed action data.
    
    Actions:
    - pick: Create topic from selected candidate and trigger analysis
    - more: Return next page of candidates
    - skip: Mark schedule as executed without creating topic
    
    Returns:
        For pick: {"success": True, "topic_id": "...", "next_step": "run-analysis"}
        For more: {"success": True, "next_step": "get-more-candidates", "page": N}
        For skip: {"success": True, "next_step": "done", "skipped": True}
    """
    orchestrator = get_flow1_orchestrator()
    
    if req.action == "pick":
        # Create topic from selected candidate
        # If topic data not provided, fetch it from Redis cache
        if not req.topic:
            if req.index is None or not req.niche_id:
                return {"success": False, "error": "Missing index or niche_id"}

            # Try to get topics from Redis cache first
            page = req.page or 1
            cache_key = f"slack_topics:{req.niche_id}:{page}"

            try:
                import json
                cached_topics = redis_client.get(cache_key)

                if cached_topics:
                    # Use cached topics (fast path)
                    topics = json.loads(cached_topics)
                    logger.info(f"✅ Retrieved {len(topics)} topics from cache for {cache_key}")
                else:
                    # Cache miss - need to re-extract (slow path)
                    logger.warning(f"⚠️ Cache miss for {cache_key}, re-extracting topics")

                    extractor = get_topic_extractor()
                    tracker = get_velocity_tracker()

                    result = await extractor.extract_topics_for_niche(
                        niche_id=req.niche_id,
                        time_period="24h",
                        max_topics=9  # Get more for pagination
                    )

                    if not result.get("success"):
                        return {"success": False, "error": "Failed to fetch candidates"}

                    topics = result.get("extracted_topics", [])

                    # Add velocity scores
                    topics_with_velocity = tracker.calculate_velocities_batch(topics, req.niche_id)

                    # Sort by velocity
                    topics_with_velocity.sort(
                        key=lambda x: x.get("velocity_score", 0),
                        reverse=True
                    )

                    topics = topics_with_velocity

                # Get the topic at the specified index
                if req.index >= len(topics):
                    return {"success": False, "error": f"Topic index {req.index} out of range (have {len(topics)} topics)"}

                req.topic = topics[req.index]

            except Exception as e:
                logger.error(f"Error retrieving topic: {e}")
                return {"success": False, "error": f"Failed to retrieve topic: {str(e)}"}

        result = await orchestrator.approve_topic(
            candidate=req.topic,
            niche_id=req.niche_id
        )
        
        if result.get("success"):
            # Mark schedule as executed (skip for test schedules)
            if req.schedule_id and not req.schedule_id.startswith("test-"):
                try:
                    await orchestrator.mark_schedule_executed(req.schedule_id)
                except Exception as e:
                    logger.warning(f"Failed to mark schedule as executed: {e}")
            return {
                "success": True,
                "topic_id": result.get("topic_id"),
                "next_step": "run-analysis"
            }
        return result
    
    elif req.action == "more":
        # Return next page info for n8n to fetch
        return {
            "success": True,
            "next_step": "get-more-candidates",
            "page": req.page or 2
        }
    
    elif req.action == "skip":
        # Mark schedule executed without creating topic
        await orchestrator.mark_schedule_executed(req.schedule_id)
        return {
            "success": True,
            "next_step": "done",
            "skipped": True
        }
    
    return {"success": False, "error": f"Unknown action: {req.action}"}


@app.post("/flow1/format-analysis-complete")
async def flow1_format_analysis_complete(topic_id: str):
    """
    Format Slack message for analysis completion notification.
    
    Called by n8n after analysis completes to notify admin.
    """
    from lib.slack_notifier import SlackNotifier
    from lib.sanity_client import get_sanity_client
    
    sanity = get_sanity_client()
    topic = sanity.get_topic_by_id(topic_id)
    
    if not topic:
        return {"success": False, "error": "Topic not found"}
    
    # Get artist name from niche reference
    niche_ref = topic.get("niche", {}).get("_ref")
    artist_name = "Unknown Artist"
    if niche_ref:
        niche = sanity.query('*[_id == $id][0]{artist->{name}}', {"id": niche_ref})
        if niche and niche.get("artist"):
            artist_name = niche["artist"].get("name", artist_name)
    
    notifier = SlackNotifier()
    message = notifier.format_analysis_complete_message(
        artist_name=artist_name,
        topic_title=topic.get("title", "Untitled"),
        topic_id=topic_id
    )
    
    return {"success": True, "slack_message": message}


# ==================== Flow 1 Manual Testing ====================


@app.post("/flow1/test-trigger/{artist_id}")
async def flow1_test_trigger(
    artist_id: str,
    skip_crawl: bool = False,
    per_page: int = 3
):
    """
    Manual test trigger for Flow 1 - bypasses schedule checks.

    Use this endpoint to test the full Flow 1 pipeline for any artist
    without waiting for their schedule to be due.

    Steps performed:
    1. Get artist's niche config
    2. Trigger crawl (unless skip_crawl=True)
    3. Get topic candidates
    4. Return candidates for manual review

    Args:
        artist_id: Sanity artist document ID
        skip_crawl: If True, skip crawl and use existing data (faster for testing)
        per_page: Number of topic candidates to return (default 3)

    Returns:
        {
            "success": True,
            "artist": {...},
            "niche": {...},
            "crawl_result": {...},  # if crawl was run
            "candidates": {...},
            "next_steps": {
                "approve_url": "/flow1/approve-topic",
                "more_topics_url": "/flow1/candidates/{niche_id}?page=2"
            }
        }
    """
    from lib.sanity_client import get_sanity_client

    sanity = get_sanity_client()
    orchestrator = get_flow1_orchestrator()

    # 1. Get artist with niche config
    artist = sanity.query(
        '''*[_type == "artist" && _id == $id][0]{
            _id,
            name,
            primaryFlowType,
            contentFocus,
            excludeKeywords,
            "nicheConfig": nicheConfig->{
                _id,
                name,
                coreKeywords,
                trendingKeywords,
                excludeKeywords,
                platforms,
                crawlSchedule
            }
        }''',
        {"id": artist_id}
    )

    if not artist:
        raise HTTPException(status_code=404, detail=f"Artist not found: {artist_id}")

    niche = artist.get("nicheConfig")
    if not niche:
        raise HTTPException(
            status_code=400,
            detail=f"Artist '{artist.get('name')}' has no nicheConfig. Configure one in Sanity Studio."
        )

    niche_id = niche.get("_id")
    result = {
        "success": True,
        "test_mode": True,
        "artist": {
            "_id": artist.get("_id"),
            "name": artist.get("name"),
            "primaryFlowType": artist.get("primaryFlowType"),
            "contentFocus": artist.get("contentFocus", [])
        },
        "niche": {
            "_id": niche_id,
            "name": niche.get("name"),
            "coreKeywords": niche.get("coreKeywords", []),
            "platforms": niche.get("platforms", [])
        }
    }

    # 2. Trigger crawl (unless skipped)
    if not skip_crawl:
        crawl_result = await orchestrator.run_scheduled_crawl(
            niche_id,
            wait_for_results=True,
            max_wait_seconds=120
        )
        result["crawl_result"] = crawl_result
    else:
        result["crawl_result"] = {"skipped": True, "reason": "skip_crawl=True"}

    # 3. Get topic candidates
    candidates = await orchestrator.get_topic_candidates(
        niche_id=niche_id,
        limit=per_page,
        page=1,
        time_period="week"
    )
    result["candidates"] = candidates

    # 4. Provide next step URLs
    result["next_steps"] = {
        "approve_topic": {
            "method": "POST",
            "url": "/flow1/approve-topic",
            "body": {
                "niche_id": niche_id,
                "candidate": "<select from candidates.topics[N]>"
            }
        },
        "more_topics": {
            "method": "GET",
            "url": f"/flow1/candidates/{niche_id}?page=2&per_page={per_page}"
        },
        "run_analysis": {
            "method": "POST",
            "url": "/flow1/run-analysis/{topic_id}",
            "note": "Call after approve_topic returns topic_id"
        }
    }

    return result


@app.get("/flow1/test-artists")
async def flow1_get_testable_artists():
    """
    Get all artists configured for Flow 1 (social crawler) testing.

    Returns artists with:
    - primaryFlowType == "social"
    - nicheConfig configured

    Useful for finding artist IDs to use with /flow1/test-trigger/{artist_id}
    """
    from lib.sanity_client import get_sanity_client

    sanity = get_sanity_client()

    artists = sanity.query('''
        *[_type == "artist" && primaryFlowType == "social" && defined(nicheConfig)]{
            _id,
            name,
            primaryFlowType,
            contentFocus,
            "nicheConfig": nicheConfig->{
                _id,
                name,
                coreKeywords,
                platforms,
                crawlSchedule
            }
        } | order(name asc)
    ''') or []

    return {
        "success": True,
        "count": len(artists),
        "artists": artists,
        "usage": "POST /flow1/test-trigger/{artist_id} to test any artist"
    }


@app.get("/flow1/candidates-clustered/{niche_id}")
async def flow1_get_candidates_clustered(
    niche_id: str,
    clusters: int = 3,
    per_cluster: int = 1,
    time_period: str = "week"
):
    """
    Get diverse topic candidates using clustering.

    Instead of returning top N by engagement score, this endpoint:
    1. Gets all available topics
    2. Clusters them by content similarity
    3. Returns top topic from each cluster

    This ensures diversity when human asks for "more topics".

    Args:
        niche_id: Sanity niche config document ID
        clusters: Number of topic clusters (default 3)
        per_cluster: Topics per cluster (default 1)
        time_period: 24h, week, or year

    Returns:
        {"topics": [...], "clusters": [...], "diversity_score": 0.85}
    """
    orchestrator = get_flow1_orchestrator()

    # Get more topics than needed for clustering
    result = await orchestrator.get_topic_candidates(
        niche_id=niche_id,
        limit=clusters * per_cluster * 5,  # Get 5x for good clustering
        page=1,
        time_period=time_period
    )

    if not result.get("success") or not result.get("topics"):
        return result

    all_topics = result.get("topics", [])

    # Simple clustering by keyword overlap
    # (In production, use embeddings for better clustering)
    clustered_topics = _cluster_topics_by_keywords(all_topics, clusters, per_cluster)

    return {
        "success": True,
        "niche_id": niche_id,
        "clustering_method": "keyword_overlap",
        "total_available": len(all_topics),
        "clusters_requested": clusters,
        "topics": clustered_topics,
        "diversity_note": "Topics selected from different content clusters for variety"
    }


def _cluster_topics_by_keywords(topics: List[Dict], num_clusters: int, per_cluster: int) -> List[Dict]:
    """
    Simple keyword-based clustering for topic diversity.

    Groups topics by keyword overlap and returns top from each group.
    """
    if len(topics) <= num_clusters * per_cluster:
        return topics[:num_clusters * per_cluster]

    # Extract keywords/titles for clustering
    clusters = []
    used_indices = set()

    for _ in range(num_clusters):
        best_topic = None
        best_idx = -1
        min_overlap = float('inf')

        for i, topic in enumerate(topics):
            if i in used_indices:
                continue

            # Calculate overlap with already selected topics
            topic_words = set(topic.get("title", "").lower().split())
            topic_words.update(topic.get("keywords", []))

            overlap = 0
            for cluster in clusters:
                cluster_words = set(cluster.get("title", "").lower().split())
                cluster_words.update(cluster.get("keywords", []))
                overlap += len(topic_words & cluster_words)

            # Prefer topics with less overlap (more diverse)
            # But also consider engagement score
            score = topic.get("z_score_velocity", 0) or topic.get("likes", 0) / 1000
            diversity_score = score - (overlap * 0.5)

            if best_topic is None or (overlap < min_overlap) or (overlap == min_overlap and score > best_topic.get("z_score_velocity", 0)):
                best_topic = topic
                best_idx = i
                min_overlap = overlap

        if best_topic:
            clusters.append(best_topic)
            used_indices.add(best_idx)

    return clusters


# ==================== AI Topic Extraction (Phase 2) ====================

from lib.topic_extractor import get_topic_extractor
from lib.velocity_tracker import get_velocity_tracker


@app.post("/flow1/extract-topics/{niche_id}")
async def flow1_extract_topics(
    niche_id: str,
    time_period: str = "24h",
    max_topics: int = 10
):
    """
    Extract AI-analyzed topics from raw MySQL data.

    This is the core of the new perception pipeline:
    1. Fetches raw posts from MySQL (XHS, Douyin, Bilibili)
    2. Uses Gemini LLM to cluster and normalize topics
    3. Extracts keywords, sentiment, controversy score
    4. Returns structured ExtractedTopic objects

    Args:
        niche_id: Sanity niche config document ID
        time_period: "24h" | "week" | "all" (default: "24h")
        max_topics: Maximum topics to extract (default: 10)

    Returns:
        {
            "success": true,
            "niche_id": "...",
            "niche_name": "Fashion OOTD",
            "extracted_topics": [
                {
                    "normalized_title": "夏季防晒技巧大全",
                    "keywords": ["防晒", "夏季护肤"],
                    "sentiment": "positive",
                    "controversy_score": 0.15,
                    "summary": "...",
                    "hook_angles": ["..."],
                    "source_posts": [...]
                }
            ],
            "raw_posts_processed": 150,
            "clusters_found": 5
        }
    """
    extractor = get_topic_extractor()

    result = await extractor.extract_topics_for_niche(
        niche_id=niche_id,
        time_period=time_period,
        max_topics=max_topics
    )

    return result


@app.get("/flow1/topic-velocity/{niche_id}")
async def flow1_get_topic_velocity(niche_id: str):
    """
    Get velocity statistics for a niche.

    Returns baseline, spike threshold, and cached topic count.

    Args:
        niche_id: Sanity niche config document ID

    Returns:
        {
            "niche_id": "...",
            "baseline": 1000.0,
            "spike_threshold": 3.0,
            "cached_topics": 25,
            "redis_available": true
        }
    """
    tracker = get_velocity_tracker()
    return tracker.get_velocity_stats(niche_id)


class ScoreTopicsRequest(BaseModel):
    """Request body for scoring topics against an artist."""
    artist_id: str
    topics: Optional[List[Dict]] = None  # If None, use extracted topics from niche


@app.post("/flow1/score-topics/{niche_id}")
async def flow1_score_topics(niche_id: str, request: ScoreTopicsRequest):
    """
    Score extracted topics against an artist profile.

    Calculates:
    1. Velocity score (Z-Score based trend detection)
    2. Artist relevance (embedding similarity to backstory)
    3. Final combined score

    Args:
        niche_id: Sanity niche config document ID
        request.artist_id: Sanity artist document ID
        request.topics: Optional list of topics (if None, extracts fresh)

    Returns:
        {
            "success": true,
            "scored_topics": [
                {
                    "normalized_title": "...",
                    "velocity_score": 2.3,
                    "trend_direction": "rising",
                    "artist_relevance": 0.87,
                    "final_score": 0.85,
                    ...
                }
            ]
        }
    """
    from lib.sanity_client import get_sanity_client

    extractor = get_topic_extractor()
    tracker = get_velocity_tracker()
    sanity = get_sanity_client()

    # Get topics (either provided or extract fresh)
    if request.topics:
        topics = request.topics
    else:
        result = await extractor.extract_topics_for_niche(
            niche_id=niche_id,
            time_period="24h",
            max_topics=20
        )
        if not result.get("success"):
            return result
        topics = result.get("extracted_topics", [])

    if not topics:
        return {"success": False, "error": "No topics to score"}

    # Get artist profile for relevance scoring
    artist = sanity.query(
        '*[_type == "artist" && _id == $id][0]{name, backstory, nicheConfig}',
        {"id": request.artist_id}
    )

    if not artist:
        return {"success": False, "error": f"Artist not found: {request.artist_id}"}

    # Calculate velocities
    topics_with_velocity = tracker.calculate_velocities_batch(topics, niche_id)

    # Calculate final scores
    scored_topics = []
    for topic in topics_with_velocity:
        # Simple relevance scoring (can be enhanced with embeddings)
        # For now, use avg_hotness as proxy
        velocity_score = topic.get("velocity_score", 0)
        avg_hotness = topic.get("avg_hotness", 0)

        # Normalize scores to 0-1 range
        velocity_normalized = min(max(velocity_score / 5.0, 0), 1)  # Z-score of 5 = max
        hotness_normalized = min(avg_hotness / 100000, 1)  # 100k hotness = max

        # Combined score (can be weighted by artist.scoringWeights)
        final_score = (
            velocity_normalized * 0.4 +
            hotness_normalized * 0.4 +
            (1 - topic.get("controversy_score", 0)) * 0.2  # Lower controversy = higher score
        )

        topic["final_score"] = round(final_score, 3)
        topic["artist_relevance"] = round(hotness_normalized, 3)  # Placeholder
        scored_topics.append(topic)

    # Sort by final score
    scored_topics.sort(key=lambda x: x.get("final_score", 0), reverse=True)

    return {
        "success": True,
        "niche_id": niche_id,
        "artist_id": request.artist_id,
        "artist_name": artist.get("name", "Unknown"),
        "scored_topics": scored_topics,
        "total_scored": len(scored_topics)
    }


@app.get("/flow1/candidates-ai/{niche_id}")
async def flow1_get_candidates_ai(
    niche_id: str,
    artist_id: Optional[str] = None,
    max_topics: int = 3,
    time_period: str = "24h"
):
    """
    Get AI-extracted topic candidates (enhanced version of candidates-clustered).

    This is the new primary endpoint for getting topic candidates:
    1. Extracts topics using LLM clustering
    2. Calculates velocity scores
    3. Optionally scores against artist profile
    4. Returns diverse, AI-analyzed topics

    Args:
        niche_id: Sanity niche config document ID
        artist_id: Optional artist ID for relevance scoring
        max_topics: Maximum topics to return (default: 3)
        time_period: "24h" | "week" | "all"

    Returns:
        {
            "success": true,
            "topics": [
                {
                    "normalized_title": "AI-generated topic name",
                    "keywords": [...],
                    "sentiment": "positive",
                    "velocity_score": 2.3,
                    "trend_direction": "rising",
                    "source_posts": [...],
                    ...
                }
            ]
        }
    """
    extractor = get_topic_extractor()
    tracker = get_velocity_tracker()

    # Extract topics
    result = await extractor.extract_topics_for_niche(
        niche_id=niche_id,
        time_period=time_period,
        max_topics=max_topics * 3  # Get more for filtering
    )

    if not result.get("success"):
        return result

    topics = result.get("extracted_topics", [])

    # Add velocity scores
    topics_with_velocity = tracker.calculate_velocities_batch(topics, niche_id)

    # Update baseline with new data
    await tracker.update_baseline(niche_id, topics_with_velocity)

    # Sort by velocity and limit
    topics_with_velocity.sort(
        key=lambda x: x.get("velocity_score", 0),
        reverse=True
    )
    final_topics = topics_with_velocity[:max_topics]

    return {
        "success": True,
        "niche_id": niche_id,
        "niche_name": result.get("niche_name", "Unknown"),
        "topics": final_topics,
        "total_available": len(final_topics),
        "raw_posts_processed": result.get("raw_posts_processed", 0),
        "extraction_method": "llm_clustering",
        "velocity_enabled": True
    }


# ==================== Artist Niche Monitoring ====================


class ArtistNicheCrawlRequest(BaseModel):
    """Request to crawl keywords for an artist's niche."""
    artist_id: str  # Sanity artist document ID
    run_analysis: bool = True  # If True, run full BettaFish analysis after crawl


@app.post("/bettafish/artist-niche-crawl")
async def crawl_artist_niche(req: ArtistNicheCrawlRequest):
    """
    Crawl data for an artist's configured niche keywords.
    
    Fetches the artist's nicheConfig from Sanity and:
    1. Extracts coreKeywords and platforms
    2. Runs MediaCrawlerPro for each keyword
    3. (Optional) Runs BettaFish full analysis
    4. Updates lastCrawledAt in Sanity
    
    Usage:
        POST /bettafish/artist-niche-crawl
        {
            "artist_id": "abc123",
            "run_analysis": true
        }
    
    Prerequisites:
    - Artist must have a nicheConfig reference in Sanity
    - nicheConfig must have coreKeywords defined
    """
    from lib.sanity_client import get_sanity_client
    from lib.forum_engine import get_forum_engine
    import asyncio
    
    logger.info(f"🎯 Starting niche crawl for artist: {req.artist_id}")
    
    # 1. Fetch artist and nicheConfig from Sanity
    sanity = get_sanity_client()
    
    artist = sanity.query(
        '*[_type == "artist" && _id == $id][0]{name, niche, nicheConfig->{name, coreKeywords, platforms, crawlFrequency}}',
        {"id": req.artist_id}
    )
    
    if not artist:
        raise HTTPException(status_code=404, detail=f"Artist {req.artist_id} not found")
    
    niche_config = artist.get("nicheConfig")
    if not niche_config:
        raise HTTPException(
            status_code=400, 
            detail=f"Artist {artist.get('name')} has no nicheConfig. Please configure keywords in Sanity."
        )
    
    keywords = niche_config.get("coreKeywords", [])
    platforms = niche_config.get("platforms", ["xhs"])
    
    if not keywords:
        raise HTTPException(
            status_code=400,
            detail=f"NicheConfig {niche_config.get('name')} has no coreKeywords defined"
        )
    
    logger.info(f"📊 Artist: {artist.get('name')}")
    logger.info(f"📊 Keywords: {keywords}")
    logger.info(f"📊 Platforms: {platforms}")
    
    # 2. Run crawl and analysis for each keyword
    results = []
    fe = get_forum_engine()
    loop = asyncio.get_event_loop()
    
    for keyword in keywords[:5]:  # Limit to 5 keywords per crawl
        logger.info(f"🔄 Processing keyword: {keyword}")
        
        try:
            if req.run_analysis:
                # Full analysis with crawl
                result = await loop.run_in_executor(
                    None,
                    lambda k=keyword: fe.run_full_analysis(
                        query=k,
                        crawl_first=True,
                        platforms=platforms,
                        generate_pdf=False
                    )
                )
            else:
                # Crawl only (via direct MediaCrawlerPro call)
                import subprocess
                from pathlib import Path
                
                mediacrawler_path = Path("/home/jimmy/Documents/mcn/external/MediaCrawlerPro-Python")
                
                crawl_results = {}
                for platform in platforms:
                    crawl_cmd = [
                        str(mediacrawler_path / ".venv/bin/python"),
                        "main.py",
                        "--platform", platform,
                        "--type", "search",
                        "--keywords", keyword
                    ]
                    
                    proc = subprocess.run(
                        crawl_cmd,
                        capture_output=True,
                        text=True,
                        timeout=300,
                        cwd=str(mediacrawler_path)
                    )
                    crawl_results[platform] = {"success": proc.returncode == 0}
                
                result = {"success": True, "crawl_results": crawl_results}
            
            results.append({
                "keyword": keyword,
                "success": result.get("success", False),
                "report_path": result.get("final_report", {}).get("html_path") if req.run_analysis else None
            })
            
        except Exception as e:
            logger.error(f"Failed to process {keyword}: {e}")
            results.append({
                "keyword": keyword,
                "success": False,
                "error": str(e)
            })
    
    # 3. Update lastCrawledAt in Sanity
    from datetime import datetime, timezone
    try:
        sanity.patch(
            niche_config.get("_id"),
            {"lastCrawledAt": datetime.now().isoformat()}
        )
    except Exception as e:
        logger.warning(f"Failed to update lastCrawledAt: {e}")
    
    return {
        "success": True,
        "artist": artist.get("name"),
        "niche": niche_config.get("name"),
        "keywords_processed": len(results),
        "results": results
    }


@app.get("/bettafish/niches-due-crawl")
async def get_niches_due_for_crawl():
    """
    Get all nicheConfigs that are due for crawling based on their crawlSchedule.
    
    Supports flexible scheduling with:
    - Specific times of day (e.g., 09:00, 14:00)
    - Specific days of week (for weekly/custom)
    - Timezone-aware checking
    - Legacy crawlFrequency fallback
    """
    from lib.sanity_client import get_sanity_client
    from datetime import datetime, timezone
    
    sanity = get_sanity_client()
    
    # Get all niche configs
    niches = sanity.get_niches_due_for_crawl()
    
    now = datetime.now(timezone.utc)
    due_niches = []
    
    for niche in niches:
        if sanity.is_niche_due_for_crawl(niche, now):
            schedule = niche.get("crawlSchedule", {})
            freq = schedule.get("frequency") or niche.get("crawlFrequency", "manual")
            times = schedule.get("times", [])
            days = schedule.get("days", [])
            
            due_niches.append({
                "id": niche.get("_id"),
                "name": niche.get("name"),
                "frequency": freq,
                "scheduled_times": times,
                "scheduled_days": days,
                "last_crawled": niche.get("lastCrawledAt"),
                "keywords_count": len(niche.get("coreKeywords", []))
            })
    
    return {
        "due_count": len(due_niches),
        "checked_at": now.isoformat(),
        "niches": due_niches
    }


# =============================================
# Media Download Endpoints (Phase 1: Media Capture)
# =============================================

class MediaDownloadRequest(BaseModel):
    """Request to download media assets for a topic."""
    topic_id: str
    platforms: List[str] = ["xhs", "douyin"]  # Default to both platforms

class MediaAssetInfo(BaseModel):
    """Information about a downloaded media asset."""
    id: str
    type: str  # "image" or "video"
    platform: str
    source_url: str
    local_path: Optional[str] = None
    source_id: str
    title: Optional[str] = None

class MediaDownloadResponse(BaseModel):
    """Response from media download request."""
    status: str  # "queued"
    task_id: str
    topic_id: str
    platforms: List[str]

class MediaStatusResponse(BaseModel):
    """Status of media download task."""
    status: str  # "queued", "processing", "completed", "failed"
    topic_id: Optional[str] = None
    platforms: Optional[List[str]] = None
    downloaded: int = 0
    failed: int = 0
    assets: List[MediaAssetInfo] = []
    error: Optional[str] = None

@app.post("/media/download", response_model=MediaDownloadResponse)
async def download_media(request: MediaDownloadRequest):
    """
    Download media assets for a topic from specified platforms.

    This endpoint:
    1. Queries MediaCrawlerPro MySQL for media URLs
    2. Downloads media files to local cache
    3. Updates Sanity topic with media_assets

    Args:
        request: MediaDownloadRequest with topic_id and platforms

    Returns:
        MediaDownloadResponse with task_id for status tracking
    """
    # Validate platforms
    valid_platforms = ["xhs", "douyin", "weibo", "bilibili", "kuaishou"]
    invalid = [p for p in request.platforms if p not in valid_platforms]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid platforms: {invalid}. Valid: {valid_platforms}"
        )

    # Enqueue task
    task_id = redis_client.enqueue_task(
        task_type="media_download",
        params={
            "topic_id": request.topic_id,
            "platforms": request.platforms
        },
        priority=10  # Normal priority
    )

    logger.info(f"📥 Media download queued: {task_id} for topic {request.topic_id}")

    return MediaDownloadResponse(
        status="queued",
        task_id=task_id,
        topic_id=request.topic_id,
        platforms=request.platforms
    )

@app.get("/media/status/{task_id}", response_model=MediaStatusResponse)
async def get_media_status(task_id: str):
    """
    Get status of media download task.

    Args:
        task_id: Task ID returned from /media/download

    Returns:
        MediaStatusResponse with download progress and assets
    """
    info = redis_client.get_task_info(task_id)
    if not info:
        raise HTTPException(status_code=404, detail="Task not found")

    # Build response
    response = MediaStatusResponse(
        status=info["status"],
        topic_id=info.get("params", {}).get("topic_id"),
        platforms=info.get("params", {}).get("platforms", [])
    )

    # Add result data if available
    if info.get("result"):
        result = info["result"]
        response.downloaded = result.get("downloaded", 0)
        response.failed = result.get("failed", 0)

        # Convert assets to MediaAssetInfo
        assets = result.get("assets", [])
        response.assets = [
            MediaAssetInfo(
                id=asset.get("id", ""),
                type=asset.get("type", ""),
                platform=asset.get("platform", ""),
                source_url=asset.get("source_url", ""),
                local_path=asset.get("local_path"),
                source_id=asset.get("source_id", ""),
                title=asset.get("title")
            )
            for asset in assets
        ]

    # Add error if present
    if info.get("error"):
        response.error = info["error"]

    return response


# =============================================
# Media Analysis Endpoints
# =============================================

class MediaAnalyzeRequest(BaseModel):
    """Request to analyze media assets."""
    topic_id: str
    extract_clips: bool = False

class MediaAnalyzeResponse(BaseModel):
    """Response from media analysis request."""
    status: str  # "queued"
    task_id: str
    topic_id: str

class MediaAnalysisStatusResponse(BaseModel):
    """Status of media analysis task."""
    status: str  # "queued", "processing", "completed", "failed"
    topic_id: Optional[str] = None
    analyzed_count: int = 0
    failed_count: int = 0
    error: Optional[str] = None

@app.post("/media/analyze", response_model=MediaAnalyzeResponse)
async def analyze_media(request: MediaAnalyzeRequest):
    """
    Analyze media assets for a topic using VLM (images) and Vidi (videos).

    This endpoint:
    1. Gets media_assets from Sanity topic
    2. Analyzes each asset with appropriate tool (Qwen2.5-VL or Vidi)
    3. Updates Sanity topic with VLM fields (description, quality_score, etc.)

    Args:
        request: MediaAnalyzeRequest with topic_id and options

    Returns:
        MediaAnalyzeResponse with task_id for status tracking
    """
    # Enqueue task
    task_id = redis_client.enqueue_task(
        task_type="media_analysis",
        params={
            "topic_id": request.topic_id,
            "extract_clips": request.extract_clips
        },
        priority=10  # Normal priority
    )

    logger.info(f"🔍 Media analysis queued: {task_id} for topic {request.topic_id}")

    return MediaAnalyzeResponse(
        status="queued",
        task_id=task_id,
        topic_id=request.topic_id
    )

@app.get("/media/analysis-status/{task_id}", response_model=MediaAnalysisStatusResponse)
async def get_analysis_status(task_id: str):
    """
    Get status of media analysis task.

    Args:
        task_id: Task ID returned from /media/analyze

    Returns:
        MediaAnalysisStatusResponse with analysis progress
    """
    info = redis_client.get_task_info(task_id)
    if not info:
        raise HTTPException(status_code=404, detail="Task not found")

    # Build response
    response = MediaAnalysisStatusResponse(
        status=info["status"],
        topic_id=info.get("params", {}).get("topic_id")
    )

    # Add result data if available
    if info.get("result"):
        result = info["result"]
        response.analyzed_count = result.get("analyzed_count", 0)
        response.failed_count = result.get("failed_count", 0)

    # Add error if present
    if info.get("error"):
        response.error = info["error"]

    return response


# =============================================
# Server Entry Point
# =============================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

