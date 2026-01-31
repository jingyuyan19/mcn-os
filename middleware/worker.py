import time
import sys
print("DEBUG: Worker Pre-Import", flush=True)
import os
import logging
import traceback
from lib import redis_client
from lib import comfy_driver
# Renaming/Importing the class from the file we copied
from lib.cosy_driver import CosyVoiceClient
from lib.gpu_manager_v2 import get_gpu_manager_v2

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("GPUWorker")

# Initialize Clients
cosy_client = CosyVoiceClient(host="localhost", port=50000)
OUTPUT_DIR = "/home/jimmy/Documents/mcn/outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

logger.info("👷 GPU Worker Started... Waiting for jobs.")

def process_comfy(task_id, params):
    """Handle ComfyUI Task with GPU Manager V2."""
    import asyncio

    async def _process():
        gpu_manager = get_gpu_manager_v2()

        async with gpu_manager.use_service("comfyui") as ready:
            if not ready:
                raise RuntimeError(
                    "Failed to acquire ComfyUI. "
                    f"GPU may be locked by: {gpu_manager.get_lock_holder()}"
                )

            template_name = params.get("template")
            if not template_name:
                raise ValueError("Task params missing 'template'")

            injection_params = params.get("params", {})
            logger.info(f"Worker processing params: {injection_params}")

            files = comfy_driver.execute_workflow(template_name, injection_params)
            return {"files": files}

    return asyncio.run(_process())

def process_cosy(task_id, params):
    """Handle CosyVoice Task"""
    output_path = os.path.join(OUTPUT_DIR, f"{task_id}.wav")

    resp = cosy_client.inference_zero_shot(
        tts_text=params.get('tts_text'),
        prompt_text=params.get('prompt_text'),
        prompt_wav_path=params.get('prompt_wav_path'),
        output_path=output_path
    )
    return resp

async def process_media_download(task_id, params):
    """Handle Media Download Task"""
    import asyncio
    from lib.mediacrawler_client import MediaCrawlerClient
    from lib.media_downloader import MediaDownloader
    from lib.sanity_client import get_sanity_client
    import uuid

    topic_id = params.get("topic_id")
    platforms = params.get("platforms", ["xhs", "douyin"])

    if not topic_id:
        raise ValueError("Missing topic_id in params")

    logger.info(f"📥 Starting media download for topic {topic_id}, platforms: {platforms}")

    # Initialize clients
    # Skip path validation since we only need MySQL queries, not the crawler CLI
    crawler_client = MediaCrawlerClient(skip_path_validation=True)
    downloader = MediaDownloader()
    sanity = get_sanity_client()

    # Get topic to find source posts
    topic = sanity.query('*[_id == $id][0]', {"id": topic_id})
    if not topic:
        raise ValueError(f"Topic {topic_id} not found")

    source_posts = topic.get("source_posts", [])
    if not source_posts:
        logger.warning(f"No source_posts found for topic {topic_id}")
        return {"downloaded": 0, "failed": 0, "assets": []}

    # Collect media URLs from MySQL
    all_media_urls = []

    for platform in platforms:
        # Extract post IDs for this platform
        platform_posts = [p for p in source_posts if p.get("platform") == platform]

        if platform == "xhs":
            note_ids = [p.get("post_id") for p in platform_posts if p.get("post_id")]
            if note_ids:
                media_urls = await crawler_client.get_xhs_media_urls(note_ids)
                all_media_urls.extend(media_urls)
                logger.info(f"Found {len(media_urls)} XHS media URLs")

        elif platform == "douyin":
            aweme_ids = [p.get("post_id") for p in platform_posts if p.get("post_id")]
            if aweme_ids:
                media_urls = await crawler_client.get_douyin_media_urls(aweme_ids)
                all_media_urls.extend(media_urls)
                logger.info(f"Found {len(media_urls)} Douyin media URLs")

    logger.info(f"Total media URLs to download: {len(all_media_urls)}")

    # Download media files
    downloaded_count = 0
    failed_count = 0
    assets = []

    for media_url in all_media_urls:
        try:
            local_path = await downloader.download_url(
                url=media_url["url"],
                platform=media_url["platform"],
                source_id=media_url["source_id"]
            )

            if local_path:
                asset = {
                    "id": str(uuid.uuid4()),
                    "type": media_url["type"],
                    "platform": media_url["platform"],
                    "source_url": media_url["url"],
                    "local_path": local_path,
                    "source_id": media_url["source_id"],
                    "title": media_url.get("title")
                }
                assets.append(asset)
                downloaded_count += 1
            else:
                failed_count += 1
                logger.warning(f"Failed to download: {media_url['url']}")

        except Exception as e:
            failed_count += 1
            logger.error(f"Error downloading {media_url['url']}: {e}")

    # Update Sanity topic with media_assets
    if assets:
        try:
            sanity.patch(topic_id, {"media_assets": assets})
            logger.info(f"✅ Updated topic {topic_id} with {len(assets)} media assets")
        except Exception as e:
            logger.error(f"Failed to update Sanity: {e}")

    # Cleanup
    await downloader.close()

    return {
        "downloaded": downloaded_count,
        "failed": failed_count,
        "assets": assets
    }

async def process_media_analysis(task_id, params):
    """Handle Media Analysis Task with GPU Manager V2."""
    import asyncio
    from lib.media_analyzer import MediaAnalyzer
    from lib.sanity_client import get_sanity_client
    import os

    topic_id = params.get("topic_id")
    extract_clips = params.get("extract_clips", False)

    if not topic_id:
        raise ValueError("Missing topic_id in params")

    logger.info(f"🔍 Starting media analysis for topic {topic_id}")

    # Prepare GPU for Phase 2 (Analysis)
    gpu_manager = get_gpu_manager_v2()
    logger.info("Preparing GPU for analysis phase")
    if not await gpu_manager.prepare_for_phase(2):
        logger.warning("Could not prepare GPU for analysis, proceeding anyway")

    # Initialize clients
    analyzer = MediaAnalyzer()
    sanity = get_sanity_client()

    # Get topic with media_assets
    topic = sanity.query('*[_id == $id][0]', {"id": topic_id})
    if not topic:
        raise ValueError(f"Topic {topic_id} not found")

    media_assets = topic.get("media_assets", [])
    if not media_assets:
        logger.warning(f"No media_assets found for topic {topic_id}")
        return {"analyzed_count": 0, "failed_count": 0}

    logger.info(f"Found {len(media_assets)} media assets to analyze")

    # Analyze each asset
    analyzed_count = 0
    failed_count = 0
    updated_assets = []

    for asset in media_assets:
        try:
            asset_type = asset.get("type")
            local_path = asset.get("local_path")

            if not local_path or not os.path.exists(local_path):
                logger.warning(f"Asset {asset.get('id')} has no valid local_path: {local_path}")
                failed_count += 1
                updated_assets.append(asset)
                continue

            # Get topic context for analysis
            context = topic.get("title", "")

            # Analyze based on type
            if asset_type == "image":
                logger.info(f"Analyzing image: {local_path}")
                analysis = await analyzer.analyze_image(local_path, context)

                # Update asset with VLM fields
                asset["description"] = analysis.description
                asset["quality_score"] = analysis.quality_score
                asset["text_ocr"] = analysis.text_ocr
                asset["objects"] = analysis.objects or []
                asset["broll_suitable"] = analysis.broll_suitable
                asset["mood"] = analysis.mood

                analyzed_count += 1

            elif asset_type == "video":
                logger.info(f"Analyzing video: {local_path}")

                # Prepare output directory for clips if needed
                output_dir = None
                if extract_clips:
                    output_dir = os.path.join(
                        os.path.dirname(local_path),
                        "clips"
                    )
                    os.makedirs(output_dir, exist_ok=True)

                analysis = await analyzer.analyze_video(
                    local_path,
                    context,
                    extract_clips=extract_clips,
                    output_dir=output_dir
                )

                # Update asset with VLM fields
                asset["description"] = analysis.description
                asset["quality_score"] = analysis.quality_score
                asset["broll_suitable"] = analysis.broll_suitable
                asset["mood"] = analysis.mood

                # Add clips if extracted
                if analysis.clips:
                    asset["clips"] = analysis.clips

                analyzed_count += 1

            else:
                logger.warning(f"Unknown asset type: {asset_type}")
                failed_count += 1

            updated_assets.append(asset)

        except Exception as e:
            logger.error(f"Error analyzing asset {asset.get('id')}: {e}")
            failed_count += 1
            updated_assets.append(asset)

    # Update Sanity topic with analyzed assets
    if updated_assets:
        try:
            sanity.patch(topic_id, {"media_assets": updated_assets})
            logger.info(f"✅ Updated topic {topic_id} with {analyzed_count} analyzed assets")
        except Exception as e:
            logger.error(f"Failed to update Sanity: {e}")
            raise

    return {
        "analyzed_count": analyzed_count,
        "failed_count": failed_count
    }

async def process_broll_generation(task_id, params):
    """Handle B-roll Generation Task"""
    from lib.broll_generator import BRollGenerator

    topic_id = params.get("topic_id")

    if not topic_id:
        raise ValueError("Missing topic_id in params")

    logger.info(f"🎬 Starting B-roll generation for topic {topic_id}")

    generator = BRollGenerator()
    result = await generator.generate_from_manifest(topic_id)

    logger.info(f"✅ B-roll generation complete: {result.get('generated_count')} videos, status: {result.get('status')}")

    return result


while True:
    # 1. Fetch Task (Blocking Wait)
    try:
        task_id = redis_client.get_next_task(timeout=5)
    except Exception as e:
        logger.error(f"Redis Connection Error: {e}")
        time.sleep(5)
        continue

    if not task_id:
        continue 

    try:
        # 2. Get Details
        info = redis_client.get_task_info(task_id)
        if not info:
            logger.warning(f"Task {task_id} not found in info store.")
            continue

        task_type = info['type']
        params = info.get('params', {})
        logger.info(f"▶️ Processing: {task_type} (ID: {task_id})")
        redis_client.update_status(task_id, "processing")

        success = False
        result_data = {}
        
        # 3. Route & Execute
        if task_type == "comfyui": # Keeping original comfyui handler for now
            result_data = process_comfy(task_id, params)
            success = True
        elif task_type == "comfyui_workflow": # New comfyui_workflow handler
            # This assumes 'workflow_json' is directly in params, or 'template' is used.
            # Adjust based on actual 'comfy_driver.execute_workflow' signature.
            # For now, let's assume it uses 'template' and 'params' like process_comfy.
            # If workflow_json is expected, it needs to be passed in 'params'.
            template_name = params.get("template")
            if not template_name:
                raise ValueError("Task params missing 'template' for comfyui_workflow")
            
            injection_params = params.get("params", {})
            
            # Inject comfy_host if needed, though comfy_driver usually handles this internally
            # params["comfy_host"] = f"{os.getenv('COMFY_HOST', 'localhost')}:{os.getenv('COMFY_PORT', '8188')}"
            
            files = comfy_driver.execute_workflow(template_name, injection_params)
            result_data = {"files": files}
            success = True
            
        elif task_type == "cosyvoice":
            # For CosyVoice, we might also want to purge VRAM if we are really tight,
            # but usually it's smaller. Let's start with just running it.
            # comfy_driver.free_vram() # Optional: Kill Comfy before Cosy
            result_data = process_cosy(task_id, params)
            success = True
        elif task_type == "media_download":
            # Handle media download task (async)
            import asyncio
            result_data = asyncio.run(process_media_download(task_id, params))
            success = True
        elif task_type == "media_analysis":
            # Handle media analysis task (async)
            import asyncio
            result_data = asyncio.run(process_media_analysis(task_id, params))
            success = True
        elif task_type == "broll_generation":
            # Handle B-roll generation task (async)
            import asyncio
            result_data = asyncio.run(process_broll_generation(task_id, params))
            success = True
        elif task_type == "remotion_render":
            from lib.remotion_driver import execute_render
            # Params: timeline (json), output_path
            timeline = params.get("timeline")
            if not timeline:
                raise ValueError("Remotion render task missing 'timeline'")
            
            output_filename = params.get("output_filename", f"render_{task_id}.mp4")
            
            # Ensure assets/output directory exists (Project Root)
            # Worker CWD is 'middleware', so we go up one level
            output_dir = os.path.abspath(os.path.join(os.getcwd(), "../assets/output"))
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, output_filename)
            
            success = execute_render(timeline, output_path)
            if success:
                # Return relative path for asset server
                result_data = {"video_path": f"/assets/output/{output_filename}"}
            else:
                result_data = {"error": "Render failed, check worker logs"}
        else:
            logger.error(f"Unknown task type: {task_type}")
            success = False
            result_data = {"error": f"Unknown task type: {task_type}"}

        # 4. Success / Completion
        if success:
            redis_client.update_status(task_id, "completed", result=result_data)
            logger.info(f"✅ Done: {task_type} {task_id}")
        else:
            # If success is False but no exception was raised (e.g., remotion_render failed internally)
            redis_client.update_status(task_id, "failed", error=result_data.get("error", "Task failed without specific error message"))
            logger.error(f"❌ Task failed: {task_type} {task_id} - {result_data.get('error', 'Unknown error')}")

    except Exception as e:
        logger.error(f"❌ Error processing {task_id}: {e}")
        traceback.print_exc()
        redis_client.update_status(task_id, "failed", error=str(e))

