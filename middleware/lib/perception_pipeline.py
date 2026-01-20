# -*- coding: utf-8 -*-
"""
PerceptionPipeline: The Nervous System of AI Artist MCN OS
==========================================================
Connects three input sources to unified topic generation:
1. Social Crawler (MediaCrawlerPro) → 泛娱乐赛道
2. Knowledge Base (open-notebook) → 知识类赛道
3. RSS Feed (RSSHub) → 新闻类赛道
4. Manual Injection → 人工注入 (Deep Think recommendation)

Architecture based on Deep Think consensus:
- Aggregation over deletion (merge duplicate signals)
- Z-Score normalization for cross-platform velocity
- Hard filter → Soft rank for artist matching
"""

import os
import logging
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from lib.sanity_client import get_sanity_client
from lib.ir_normalizer import get_ir_normalizer, UniversalContextSchema
from lib.intent_router import get_intent_router
from lib.doc_grader import get_doc_grader

logger = logging.getLogger("PerceptionPipeline")


@dataclass
class TopicSignal:
    """A single signal from any input source."""
    platform: str
    url: Optional[str]
    content_snippet: str
    metrics: Dict[str, Any]  # likes, comments, shares
    
    def to_sanity(self) -> Dict:
        """Convert to Sanity object format."""
        import uuid
        return {
            "_key": str(uuid.uuid4())[:8],
            "platform": self.platform,
            "url": self.url,
            "content_snippet": self.content_snippet[:500] if self.content_snippet else "",
            "metrics": {
                "likes": self.metrics.get("likes", 0),
                "comments": self.metrics.get("comments", 0),
                "shares": self.metrics.get("shares", 0),
                "captured_at": datetime.utcnow().isoformat() + "Z"
            }
        }


@dataclass
class TopicSuggestion:
    """A unified topic suggestion ready for Sanity."""
    title: str
    source_type: str  # social_crawler, knowledge_base, rss_feed, manual
    keywords: List[str]
    signals: List[TopicSignal]
    z_score_velocity: float = 0.0
    controversy_ratio: float = 0.0
    sentiment: str = "neutral"
    extracted_hooks: List[str] = None
    niche_id: Optional[str] = None
    
    def compute_fingerprint(self) -> str:
        """Generate deduplication fingerprint from title + keywords."""
        content = f"{self.title}|{'|'.join(sorted(self.keywords))}"
        return hashlib.md5(content.encode()).hexdigest()[:16]


class PerceptionPipeline:
    """
    Main orchestrator for the Perception Layer.
    
    Usage:
        pipeline = get_perception_pipeline()
        topic_id = await pipeline.ingest_signal(signal_data)
    """
    
    def __init__(self):
        self.sanity = get_sanity_client()
        self._insight_engine = None  # Lazy load
        
        # URLs for external services
        self.mediacrawler_url = os.getenv("CRAWLER_URL", "http://mediacrawler:8001")
        self.rsshub_url = os.getenv("RSSHUB_URL", "http://rsshub:1200")
        self.open_notebook_url = os.getenv("OPEN_NOTEBOOK_URL", "http://open-notebook:5055")
        
        logger.info("PerceptionPipeline initialized")
    
    @property
    def insight_engine(self):
        """Lazy load InsightEngine to avoid circular imports."""
        if self._insight_engine is None:
            from lib.insight_engine import get_insight_engine
            self._insight_engine = get_insight_engine()
        return self._insight_engine
    
    # =========================================================================
    # Main Ingestion API
    # =========================================================================
    
    async def ingest_signal(
        self,
        title: str,
        source_type: str,
        platform: str,
        content: str,
        url: Optional[str] = None,
        metrics: Optional[Dict] = None,
        keywords: Optional[List[str]] = None,
        niche_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Main entry point for all signal types.
        
        Args:
            title: Topic title
            source_type: One of 'social_crawler', 'knowledge_base', 'rss_feed', 'manual'
            platform: Source platform (xhs, douyin, rss, manual, etc.)
            content: Content snippet or summary
            url: Source URL (optional)
            metrics: Engagement metrics dict (optional)
            keywords: Extracted keywords (optional)
            niche_id: Associated niche config ID (optional)
            
        Returns:
            {"success": True, "topic_id": "...", "action": "created" | "merged"}
        """
        logger.info(f"Ingesting signal: {title[:50]}... from {source_type}/{platform}")
        
        # 1. Create signal object
        signal = TopicSignal(
            platform=platform,
            url=url,
            content_snippet=content,
            metrics=metrics or {}
        )
        
        # 2. Create topic suggestion
        topic = TopicSuggestion(
            title=title,
            source_type=source_type,
            keywords=keywords or [],
            signals=[signal],
            niche_id=niche_id
        )
        
        # 3. Check for duplicates (fingerprint + semantic matching)
        fingerprint = topic.compute_fingerprint()
        existing_topic = await self._find_similar_topic(fingerprint, title, content)
        
        if existing_topic:
            # 4a. Merge into existing topic
            return await self._merge_signal(existing_topic, signal)
        else:
            # 4b. Create new topic
            return await self._create_topic(topic, fingerprint)
    
    # =========================================================================
    # Deduplication & Aggregation
    # =========================================================================
    
    async def _find_similar_topic(
        self, 
        fingerprint: str, 
        title: str,
        content: str = "",
        time_window_hours: int = 72
    ) -> Optional[Dict]:
        """
        Find existing topic with same fingerprint or similar content.
        
        Two-stage deduplication:
        1. Exact fingerprint match (fast, hash-based)
        2. Semantic similarity via Qdrant (if fingerprint not found)
        """
        # Stage 1: Exact fingerprint match
        result = self.sanity.query(
            '*[_type == "topic" && fingerprint == $fp][0]',
            {"fp": fingerprint}
        )
        
        if result:
            logger.info(f"Found exact fingerprint match: {result.get('_id')}")
            return result
        
        # Stage 2: Semantic similarity via Qdrant
        try:
            from lib.qdrant_client import get_qdrant_client
            
            qdrant = get_qdrant_client()
            similar = await qdrant.find_similar(
                title=title,
                content=content,
                threshold=0.85,  # Deep Think recommendation
                time_window_hours=time_window_hours,
                limit=1
            )
            
            if similar:
                # Found semantically similar topic
                best_match = similar[0]
                logger.info(f"Found semantic match: {best_match['topic_id']} (score: {best_match['score']:.2f})")
                
                # Fetch full topic from Sanity
                return self.sanity.query(
                    '*[_type == "topic" && _id == $id][0]',
                    {"id": best_match["topic_id"]}
                )
                
        except Exception as e:
            logger.warning(f"Qdrant search failed (falling back to fingerprint only): {e}")
        
        return None
    
    async def _merge_signal(self, existing_topic: Dict, new_signal: TopicSignal) -> Dict:
        """
        Merge new signal into existing topic (aggregation pattern).
        Appends to signals[] array and updates velocity.
        """
        topic_id = existing_topic["_id"]
        logger.info(f"Merging signal into existing topic: {topic_id}")
        
        # Append signal to array
        self.sanity.patch(topic_id, {
            "signals": existing_topic.get("signals", []) + [new_signal.to_sanity()]
        })
        
        # TODO: Recalculate aggregated velocity
        
        return {
            "success": True,
            "topic_id": topic_id,
            "action": "merged"
        }
    
    async def _create_topic(self, topic: TopicSuggestion, fingerprint: str) -> Dict:
        """Create new topic in Sanity and store embedding in Qdrant."""
        logger.info(f"Creating new topic: {topic.title[:50]}...")
        
        # Generate client-side document ID (Sanity doesn't return ID on create)
        import uuid
        topic_id = f"topic.{uuid.uuid4().hex[:12]}"
        
        data = {
            "_id": topic_id,
            "title": topic.title,
            "source_type": topic.source_type,
            "status": "new",
            "keywords": topic.keywords,
            "signals": [s.to_sanity() for s in topic.signals],
            "z_score_velocity": topic.z_score_velocity,
            "controversy_ratio": topic.controversy_ratio,
            "sentiment": topic.sentiment,
            "extracted_hooks": topic.extracted_hooks or [],
            "fingerprint": fingerprint
        }
        
        # Add niche reference if provided
        if topic.niche_id:
            data["niche"] = {"_type": "reference", "_ref": topic.niche_id}
        
        self.sanity.create("topic", data)
        
        # Store embedding in Qdrant for future semantic matching
        try:
            from lib.qdrant_client import get_qdrant_client
            
            qdrant = get_qdrant_client()
            content = topic.signals[0].content_snippet if topic.signals else ""
            await qdrant.upsert_topic(
                topic_id=topic_id,
                title=topic.title,
                content=content,
                source_type=topic.source_type
            )
            logger.info(f"✅ Stored embedding for topic: {topic_id}")
        except Exception as e:
            logger.warning(f"Failed to store embedding in Qdrant: {e}")
        
        return {
            "success": True,
            "topic_id": topic_id,
            "action": "created"
        }
    
    # =========================================================================
    # Social Crawler Pipeline (Phase 2)
    # =========================================================================
    
    async def crawl_niche_to_topics(self, niche_id: str) -> Dict[str, Any]:
        """
        Crawl social media for a niche and create topics from results.
        
        Flow:
        1. Get niche config from Sanity (keywords, platforms)
        2. Call MediaCrawler for each platform/keyword combo
        3. Analyze with BettaFish for sentiment
        4. Create topics in Sanity with aggregation
        5. Update lastCrawledAt timestamp
        
        Args:
            niche_id: Sanity niche config document ID
            
        Returns:
            {"success": True, "topics_created": N, "topics_merged": M}
        """
        import httpx
        
        # 1. Get niche config
        niche = self.sanity.query(
            '*[_type == "nicheConfig" && _id == $id][0]',
            {"id": niche_id}
        )
        
        if not niche:
            return {"success": False, "error": f"Niche not found: {niche_id}"}
        
        niche_name = niche.get("name", "Unknown")
        keywords = niche.get("coreKeywords", []) + niche.get("trendingKeywords", [])
        platforms = niche.get("platforms", ["xhs"])
        
        logger.info(f"🕷️ Crawling niche '{niche_name}': {len(keywords)} keywords, {len(platforms)} platforms")
        
        topics_created = 0
        topics_merged = 0
        errors = []
        
        # 2. Crawl each platform
        for platform in platforms:
            for keyword in keywords[:5]:  # Limit to 5 keywords per crawl to avoid rate limits
                try:
                    # Call MediaCrawler HTTP API
                    async with httpx.AsyncClient(timeout=120.0) as client:
                        response = await client.post(
                            f"{self.mediacrawler_url}/crawl",
                            json={
                                "platform": platform,
                                "crawler_type": "search",
                                "keywords": keyword,
                                "max_notes": 20
                            }
                        )
                        
                        if response.status_code != 200:
                            errors.append(f"{platform}/{keyword}: HTTP {response.status_code}")
                            continue
                        
                        crawl_result = response.json()
                        
                    if not crawl_result.get("success"):
                        continue
                    
                    # 3. Process each result into a topic
                    # Note: Actual data comes from MySQL, this just triggers the crawl
                    # For now, create a topic from the crawl metadata
                    result = await self.ingest_signal(
                        title=f"{keyword} - {platform.upper()} 热点",
                        source_type="social_crawler",
                        platform=platform,
                        content=f"Crawl results for '{keyword}' on {platform}",
                        keywords=[keyword, niche_name],
                        niche_id=niche_id,
                        metrics={"likes": 0, "comments": 0}  # Will be enriched from BettaFish
                    )
                    
                    if result.get("action") == "created":
                        topics_created += 1
                    elif result.get("action") == "merged":
                        topics_merged += 1
                        
                except Exception as e:
                    errors.append(f"{platform}/{keyword}: {str(e)}")
                    logger.error(f"Crawl error for {platform}/{keyword}: {e}")
        
        # 4. Update lastCrawledAt
        self.sanity.update_niche_last_crawled(niche_id)
        
        logger.info(f"✅ Niche '{niche_name}' crawl complete: {topics_created} created, {topics_merged} merged")
        
        return {
            "success": True,
            "niche_id": niche_id,
            "niche_name": niche_name,
            "topics_created": topics_created,
            "topics_merged": topics_merged,
            "errors": errors if errors else None
        }
    
    async def process_crawler_results(
        self,
        platform: str,
        results: List[Dict],
        niche_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process raw MediaCrawler results into topics.
        
        Called by MediaCrawler webhook or direct integration.
        Each result should have: title, content, url, metrics (likes, comments)
        """
        topics_created = 0
        topics_merged = 0
        
        for item in results:
            try:
                # Calculate Z-Score velocity
                likes = item.get("likes", 0)
                comments = item.get("comments", 0)
                z_score = self.calculate_z_score(likes, comments, platform)
                controversy = self.calculate_controversy_ratio(likes, comments)
                
                # Create topic
                result = await self.ingest_signal(
                    title=item.get("title", "Untitled"),
                    source_type="social_crawler",
                    platform=platform,
                    content=item.get("content", "")[:500],
                    url=item.get("url"),
                    keywords=item.get("keywords", []),
                    niche_id=niche_id,
                    metrics={"likes": likes, "comments": comments, "shares": item.get("shares", 0)}
                )
                
                # Update velocity if topic was created
                if result.get("topic_id"):
                    self.sanity.patch(result["topic_id"], {
                        "z_score_velocity": z_score,
                        "controversy_ratio": controversy
                    })
                
                if result.get("action") == "created":
                    topics_created += 1
                else:
                    topics_merged += 1
                    
            except Exception as e:
                logger.error(f"Error processing crawler result: {e}")
        
        return {
            "success": True,
            "processed": len(results),
            "topics_created": topics_created,
            "topics_merged": topics_merged
        }
    
    # =========================================================================
    # Z-Score Velocity Calculation
    # =========================================================================
    
    def calculate_z_score(
        self,
        likes: int,
        comments: int,
        platform: str,
        niche: Optional[str] = None
    ) -> float:
        """
        Calculate Z-Score normalized velocity.
        
        Z = (x - μ) / σ
        
        Platform baselines (rough estimates, should be learned):
        - XHS: μ=200, σ=500
        - Douyin: μ=5000, σ=20000
        - Weibo: μ=500, σ=2000
        """
        # Platform baseline stats (rough estimates)
        baselines = {
            "xhs": {"mean": 200, "std": 500},
            "douyin": {"mean": 5000, "std": 20000},
            "weibo": {"mean": 500, "std": 2000},
            "bilibili": {"mean": 1000, "std": 5000},
            "default": {"mean": 500, "std": 1000}
        }
        
        stats = baselines.get(platform, baselines["default"])
        
        # Z-Score for likes
        z_likes = (likes - stats["mean"]) / max(stats["std"], 1)
        
        # Controversy ratio bonus (Deep Think recommendation)
        controversy = comments / max(likes, 1)
        controversy_bonus = 1.0 + min(controversy * 2, 1.0)  # Max 2x multiplier
        
        return round(z_likes * controversy_bonus, 2)
    
    def calculate_controversy_ratio(self, likes: int, comments: int) -> float:
        """Calculate controversy ratio (comments/likes)."""
        if likes == 0:
            return 0.0
        return round(comments / likes, 3)
    
    # =========================================================================
    # Research Enrichment with IR Normalizer (Perception Layer v3.0)
    # =========================================================================
    
    async def enrich_with_research(
        self,
        topic_id: str,
        research_agent: str = "auto"
    ) -> Dict[str, Any]:
        """
        Enrich a topic with deep research and normalize to UCS.
        
        This integrates the research agents (BettaFish, MiroThinker, OpenNotebook)
        and outputs a unified UniversalContextSchema for consistent downstream use.
        
        Args:
            topic_id: Sanity topic document ID
            research_agent: "bettafish", "mirothinker", "open_notebook", or "auto"
            
        Returns:
            {
                "success": True,
                "topic_id": "...",
                "ucs": {...},  # UniversalContextSchema
                "research_agent": "bettafish"
            }
        """
        # 1. Get topic from Sanity
        topic = self.sanity.query(
            '*[_type == "topic" && _id == $id][0]',
            {"id": topic_id}
        )
        
        if not topic:
            return {"success": False, "error": f"Topic not found: {topic_id}"}
        
        title = topic.get("title", "")
        source_type = topic.get("source_type", "social_crawler")
        signals = topic.get("signals", [])
        
        # 2. Determine research agent if auto
        if research_agent == "auto":
            research_agent = self._select_research_agent(source_type, topic)
        
        logger.info(f"Enriching topic {topic_id} with {research_agent}")
        
        normalizer = get_ir_normalizer()
        ucs = None
        raw_output = None
        
        # 3. Call appropriate research agent
        try:
            if research_agent == "bettafish":
                ucs, raw_output = await self._research_with_bettafish(topic, normalizer)
                
            elif research_agent == "mirothinker":
                ucs, raw_output = await self._research_with_mirothinker(topic, normalizer)
                
            elif research_agent == "open_notebook":
                ucs, raw_output = await self._research_with_opennotebook(topic, normalizer)
                
            else:
                return {"success": False, "error": f"Unknown research agent: {research_agent}"}
                
        except Exception as e:
            logger.error(f"Research enrichment failed: {e}")
            return {"success": False, "error": str(e)}
        
        # 4. Store UCS summary in topic
        if ucs:
            self.sanity.patch(topic_id, {
                "bettafish_summary": ucs.get("core_event", "")[:500],
                "sentiment": ucs.get("public_sentiment", {}).get("emotion", "neutral"),
                "extracted_hooks": ucs.get("analysis", {}).get("hook_angles", [])[:5]
            })
        
        return {
            "success": True,
            "topic_id": topic_id,
            "ucs": ucs,
            "research_agent": research_agent
        }
    
    def _select_research_agent(self, source_type: str, topic: Dict) -> str:
        """
        Auto-select research agent based on source type and topic properties.
        
        Rules:
        - social_crawler → BettaFish (has URLs to analyze)
        - knowledge_base → OpenNotebook (has notebook context)
        - rss_feed → MiroThinker (needs web research)
        - manual → MiroThinker (needs external enrichment)
        """
        if source_type == "social_crawler":
            return "bettafish"
        elif source_type == "knowledge_base":
            return "open_notebook"
        else:
            return "mirothinker"
    
    async def _research_with_bettafish(
        self,
        topic: Dict,
        normalizer
    ) -> tuple:
        """
        Research with BettaFish and normalize to UCS.
        
        BettaFish is best for social crawler topics where we have
        actual URLs and engagement data to analyze.
        """
        from lib.bettafish_client import get_bettafish_client
        
        bettafish = get_bettafish_client()
        
        # Get first signal URL for analysis
        signals = topic.get("signals", [])
        if not signals:
            # No URL, generate IR from title
            ir_output = {
                "title": topic.get("title", ""),
                "blocks": [],
                "platform": "unknown"
            }
        else:
            first_signal = signals[0]
            platform = first_signal.get("platform", "xhs")
            
            # Get IR from BettaFish
            ir_output = bettafish.get_topic_ir(
                topic_id=topic.get("_id", ""),
                platform=platform
            )
        
        # Normalize to UCS
        ucs = normalizer.normalize_bettafish_ir(
            ir_output,
            source_type=topic.get("source_type", "social")
        )
        
        return ucs, ir_output
    
    async def _research_with_mirothinker(
        self,
        topic: Dict,
        normalizer
    ) -> tuple:
        """
        Research with MiroThinker and normalize to UCS.
        
        MiroThinker is best for RSS/news topics that need
        web research to gather context.
        """
        from lib.mirothinker_client import get_mirothinker_client
        
        mirothinker = get_mirothinker_client()
        
        # Build research query from topic
        title = topic.get("title", "")
        keywords = topic.get("keywords", [])
        
        query = f"{title}. Keywords: {', '.join(keywords[:5])}"
        
        # Run deep research
        report = await mirothinker.deep_research(
            query=query,
            max_turns=30,  # Balance speed and depth
            min_scraped_pages=3
        )
        
        # Normalize to UCS
        ucs = normalizer.normalize_mirothinker_report(
            report,
            source_type=topic.get("source_type", "rss")
        )
        
        return ucs, report
    
    async def _research_with_opennotebook(
        self,
        topic: Dict,
        normalizer
    ) -> tuple:
        """
        Research with OpenNotebook and normalize to UCS.
        
        OpenNotebook is best for knowledge_base topics where we
        have curated documents to query.
        """
        from lib.open_notebook_client import get_open_notebook_client
        
        client = get_open_notebook_client()
        
        # Get artist's notebook ID (if assigned)
        artist_ref = topic.get("assigned_artist", {})
        if artist_ref and artist_ref.get("_ref"):
            artist = self.sanity.query(
                '*[_type == "artist" && _id == $id][0]',
                {"id": artist_ref["_ref"]}
            )
            notebook_id = artist.get("knowledgeBase", {}).get("notebookId")
        else:
            notebook_id = None
        
        if not notebook_id:
            # Fallback: list notebooks and use first one
            notebooks = await client.list_notebooks()
            if notebooks:
                notebook_id = notebooks[0].get("id")
        
        if not notebook_id:
            return None, {"error": "No notebook available"}
        
        # Ask the knowledge base
        title = topic.get("title", "")
        rag_result = await client.ask(
            notebook_id=notebook_id,
            question=f"Provide key insights about: {title}"
        )
        
        # Normalize to UCS
        ucs = normalizer.normalize_opennotebook_rag(
            rag_result,
            source_type="knowledge_base"
        )
        
        return ucs, rag_result
    
    async def generate_script_from_topic(
        self,
        topic_id: str,
        artist_id: Optional[str] = None,
        research_agent: str = "auto"
    ) -> Dict[str, Any]:
        """
        Complete flow: Topic → Research → UCS → Gemini → Script
        
        This is the main entry point for script generation that uses
        the normalized UCS format for consistent Gemini prompting.
        
        Args:
            topic_id: Sanity topic ID
            artist_id: Optional artist to generate for (uses assigned if None)
            research_agent: Which agent to use for enrichment
            
        Returns:
            {
                "success": True,
                "topic_id": "...",
                "script": {...},
                "ucs": {...}
            }
        """
        # 1. Enrich with research
        enrichment = await self.enrich_with_research(topic_id, research_agent)
        
        if not enrichment.get("success"):
            return enrichment
        
        ucs = enrichment.get("ucs")
        
        # 2. Get artist context
        topic = self.sanity.query(
            '*[_type == "topic" && _id == $id][0]',
            {"id": topic_id}
        )
        
        if artist_id:
            artist_ref = artist_id
        else:
            artist_ref = topic.get("assigned_artist", {}).get("_ref")
        
        artist = None
        if artist_ref:
            artist = self.sanity.query(
                '*[_type == "artist" && _id == $id][0]',
                {"id": artist_ref}
            )
        
        # 3. Generate script with Gemini using UCS
        script = await self._generate_script_with_gemini(ucs, artist, topic)
        
        # 4. Update topic with generated script reference
        if script.get("success"):
            self.sanity.patch(topic_id, {
                "status": "scripted"
            })
        
        return {
            "success": True,
            "topic_id": topic_id,
            "script": script,
            "ucs": ucs,
            "research_agent": enrichment.get("research_agent")
        }
    
    async def _generate_script_with_gemini(
        self,
        ucs: Dict,
        artist: Optional[Dict],
        topic: Dict
    ) -> Dict[str, Any]:
        """
        Generate video script using Gemini with UCS context.
        
        The UCS provides a consistent format regardless of which
        research agent was used (BettaFish, MiroThinker, OpenNotebook).
        """
        import httpx
        import json
        import re
        
        # Build artist persona context
        persona = ""
        if artist:
            persona = f"""
艺人信息:
- 艺名: {artist.get('name', 'Unknown')}
- 赛道: {artist.get('niche', 'general')}
- 风格: {artist.get('voiceStyle', 'professional')}
- 人设: {artist.get('backstory', '')[:200]}
"""
        
        # Build prompt from UCS
        prompt = f"""基于以下研究内容，生成一个60秒的短视频脚本。

## 核心事件
{ucs.get('core_event', topic.get('title', ''))}

## 公众情绪
情感倾向: {ucs.get('public_sentiment', {}).get('emotion', 'neutral')}
热门评论: {', '.join(ucs.get('public_sentiment', {}).get('key_quotes', [])[:3])}

## 分析洞察
{ucs.get('analysis', {}).get('implications', '')}

## 可用钩子
{chr(10).join(['- ' + h for h in ucs.get('analysis', {}).get('hook_angles', [])[:3]])}

## 视觉线索 (流行词汇)
{', '.join(ucs.get('visual_cues', [])[:5])}

{persona}

## 输出要求
请返回JSON格式的脚本:
{{
  "title": "吸睛标题",
  "hook": "开场5秒钩子",
  "scenes": [
    {{
      "scene_number": 1,
      "script": "解说词",
      "visual_prompt": "Visual description",
      "duration_seconds": 10
    }}
  ]
}}
"""
        
        try:
            antigravity_url = os.getenv("ANTIGRAVITY_BASE_URL", "http://127.0.0.1:8045/v1")
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{antigravity_url}/chat/completions",
                    json={
                        "model": "gemini-2.0-flash",
                        "messages": [
                            {"role": "system", "content": "你是专业的短视频编剧，擅长创作病毒式传播的内容。只返回JSON，不要其他解释。"},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.7
                    }
                )
                result = response.json()
            
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "{}")
            
            # Extract JSON from markdown if present
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
            if json_match:
                content = json_match.group(1)
            
            script = json.loads(content)
            script["success"] = True
            return script
            
        except Exception as e:
            logger.error(f"Script generation failed: {e}")
            return {"success": False, "error": str(e)}


# =========================================================================
# Singleton
# =========================================================================

_pipeline: Optional[PerceptionPipeline] = None


def get_perception_pipeline() -> PerceptionPipeline:
    """Get or create the PerceptionPipeline singleton."""
    global _pipeline
    if _pipeline is None:
        _pipeline = PerceptionPipeline()
    return _pipeline
