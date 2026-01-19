# -*- coding: utf-8 -*-
"""
InsightEngine Integration
=========================
Wrapper that combines BettaFish InsightEngine capabilities with our working
bettafish_client database access.

Key Features:
- LLM-optimized keyword generation (via BettaFish KeywordOptimizer)
- Uses our bettafish_client for DB access (avoids SQLAlchemy issues)
- Provides deep research with reflection

Usage:
    from lib.insight_engine import get_insight_engine
    
    engine = get_insight_engine()
    
    # Optimize keywords
    keywords = engine.optimize_keywords("AI发展趋势")
    
    # Deep research on a topic
    result = engine.research(topic_id="123", platform="xhs")
"""

import logging
import sys
import os
from typing import Dict, List, Optional, Any

logger = logging.getLogger("InsightEngine")

# Add BettaFish to path
BETTAFISH_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../external/BettaFish')
)


class InsightEngineWrapper:
    """
    Wrapper for BettaFish InsightEngine that uses our DB client.
    
    Combines:
    - BettaFish KeywordOptimizer (LLM-based keyword expansion)
    - Our bettafish_client.py (working DB access)
    - Sentiment analysis (already integrated)
    """
    
    def __init__(self):
        """Initialize InsightEngine wrapper."""
        self._keyword_optimizer = None
        self._bettafish_client = None
        logger.info("InsightEngineWrapper initialized")
    
    def _get_keyword_optimizer(self):
        """Lazy load keyword optimizer."""
        if self._keyword_optimizer is None:
            # Ensure BettaFish .env is loaded
            from dotenv import load_dotenv
            bettafish_env = os.path.join(BETTAFISH_PATH, '.env')
            if os.path.exists(bettafish_env):
                load_dotenv(bettafish_env)
                logger.info(f"Loaded BettaFish config from {bettafish_env}")
            
            if BETTAFISH_PATH not in sys.path:
                sys.path.insert(0, BETTAFISH_PATH)
            
            try:
                # Reload config after loading .env
                import importlib
                if 'config' in sys.modules:
                    importlib.reload(sys.modules['config'])
                
                from InsightEngine.tools.keyword_optimizer import KeywordOptimizer
                self._keyword_optimizer = KeywordOptimizer()
                logger.info("KeywordOptimizer loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load KeywordOptimizer: {e}")
                raise
        return self._keyword_optimizer
    
    def _get_bettafish_client(self):
        """Get our working bettafish client."""
        if self._bettafish_client is None:
            from lib.bettafish_client import BettaFishClient
            self._bettafish_client = BettaFishClient()
        return self._bettafish_client
    
    def optimize_keywords(self, query: str, context: str = "") -> Dict:
        """
        Use BettaFish KeywordOptimizer to expand query into 
        social-media-friendly keywords.
        
        Args:
            query: Original search query
            context: Additional context
            
        Returns:
            {
                "success": True,
                "original": "AI发展趋势",
                "keywords": ["AI", "人工智能", "ChatGPT", ...],
                "reasoning": "..."
            }
        """
        try:
            optimizer = self._get_keyword_optimizer()
            result = optimizer.optimize_keywords(query, context)
            
            # Clean up any malformed keywords
            clean_keywords = []
            for kw in result.optimized_keywords:
                if kw and len(kw) > 1 and kw not in ['[', ']', '{', '}']:
                    # Remove numbering prefixes
                    if kw.startswith(('1.', '2.', '3.', '4.', '5.')):
                        kw = kw.split(' ', 1)[-1] if ' ' in kw else kw
                    clean_keywords.append(kw.strip())
            
            return {
                "success": result.success,
                "original": query,
                "keywords": clean_keywords[:10],  # Limit to 10
                "reasoning": result.reasoning
            }
        except Exception as e:
            logger.error(f"Keyword optimization failed: {e}")
            return {
                "success": False,
                "original": query,
                "keywords": [query],  # Fallback to original
                "error": str(e)
            }
    
    def search_with_optimized_keywords(
        self, 
        query: str, 
        hours: int = 168,
        platforms: List[str] = None
    ) -> List[Dict]:
        """
        Search using LLM-optimized keywords.
        
        This combines:
        1. KeywordOptimizer - expands query to social media terms
        2. bettafish_client.search_topics - searches our DB
        
        Args:
            query: Original query
            hours: Look back hours
            platforms: Platforms to search
            
        Returns:
            List of matching topics
        """
        # Get optimized keywords
        opt_result = self.optimize_keywords(query)
        keywords = opt_result.get("keywords", [query])
        
        # Search for each keyword
        bf = self._get_bettafish_client()
        all_results = []
        seen_ids = set()
        
        for keyword in keywords[:5]:  # Limit to top 5 keywords
            results = bf.search_topics(
                keyword=keyword, 
                hours=hours, 
                limit=10,
                platforms=platforms
            )
            
            for r in results:
                if r['id'] not in seen_ids:
                    seen_ids.add(r['id'])
                    r['matched_keyword'] = keyword
                    all_results.append(r)
        
        # Sort by engagement
        all_results.sort(key=lambda x: x.get('likes', 0), reverse=True)
        
        logger.info(f"Found {len(all_results)} topics for '{query}' using {len(keywords)} optimized keywords")
        return all_results[:20]  # Return top 20
    
    def research(
        self, 
        topic_id: str, 
        platform: str,
        include_sentiment: bool = True
    ) -> Dict:
        """
        Perform deep research on a topic.
        
        Combines:
        - Topic IR
        - Sentiment analysis
        - Enriched CCO
        
        Args:
            topic_id: Topic ID
            platform: Platform name
            include_sentiment: Include sentiment analysis
            
        Returns:
            Comprehensive research result
        """
        bf = self._get_bettafish_client()
        
        # Get IR (includes sentiment now)
        ir = bf.get_topic_ir(topic_id, platform)
        
        # Get enriched CCO
        cco = bf.get_enriched_cco(topic_id, platform, include_sentiment=include_sentiment)
        
        return {
            "topic_id": topic_id,
            "platform": platform,
            "ir": ir,
            "cco": cco,
            "urgency": ir.get("urgency", "normal")
        }
    
    def deep_research(self, query: str, save_report: bool = False) -> Dict:
        """
        Run full deep research with BettaFish's DeepSearchAgent.
        
        This implements the COMPLETE BettaFish workflow:
        1. Generate report structure (LLM plans paragraphs)
        2. For each paragraph:
           - Initial search + summary
           - Reflection loop × N (refine search, improve summary)
        3. Generate final report
        
        Uses Antigravity Manager (zero LLM cost).
        
        Args:
            query: Research query (e.g., "小红书美妆趋势分析")
            save_report: Whether to save report to file
            
        Returns:
            {
                "success": True,
                "query": "...",
                "report": "Final report markdown...",
                "paragraphs": N,
                "reflections_per_paragraph": M
            }
        """
        try:
            # Ensure BettaFish config is loaded
            from dotenv import load_dotenv
            bettafish_env = os.path.join(BETTAFISH_PATH, '.env')
            if os.path.exists(bettafish_env):
                load_dotenv(bettafish_env)
            
            if BETTAFISH_PATH not in sys.path:
                sys.path.insert(0, BETTAFISH_PATH)
            
            # Import and run the full DeepSearchAgent
            from InsightEngine.agent import DeepSearchAgent
            
            logger.info(f"Starting deep research: {query}")
            agent = DeepSearchAgent()
            
            # Run the full research workflow
            report = agent.research(query, save_report=save_report)
            
            # Get progress stats
            stats = agent.get_progress_summary()
            
            logger.info(f"Deep research complete for: {query}")
            
            return {
                "success": True,
                "query": query,
                "report": report,
                "paragraphs": stats.get("total_paragraphs", 0),
                "completed_paragraphs": stats.get("completed_paragraphs", 0),
                "status": stats.get("status", "completed")
            }
            
        except Exception as e:
            import traceback
            logger.error(f"Deep research failed: {e}\n{traceback.format_exc()}")
            return {
                "success": False,
                "query": query,
                "error": str(e)
            }
    
    def get_related_topics(
        self, 
        topic_id: str, 
        platform: str,
        max_related: int = 5
    ) -> List[Dict]:
        """
        Find related topics using keyword optimization.
        
        Takes the topic title, optimizes keywords, and searches for similar topics.
        """
        bf = self._get_bettafish_client()
        
        # Get topic CCO for title
        cco = bf.get_topic_cco(topic_id, platform)
        title = cco.get('title', '')
        
        if not title:
            return []
        
        # Search with optimized keywords
        related = self.search_with_optimized_keywords(
            query=title,
            hours=720  # 30 days
        )
        
        # Filter out the original topic
        related = [r for r in related if r['id'] != topic_id]
        
        return related[:max_related]
    
    def search_with_citations(
        self,
        query: str,
        hours: int = 168,
        limit: int = 20
    ) -> Dict:
        """
        Search with citation grounding - returns database record IDs.
        
        This prevents hallucination by ensuring every claim can be
        traced back to a specific database record.
        
        Args:
            query: Search query
            hours: Look back hours
            limit: Maximum results
            
        Returns:
            {
                "success": True,
                "citations": [
                    {
                        "id": "record_123",
                        "platform": "xhs",
                        "title": "...",
                        "content_preview": "...",
                        "url": "..."
                    }
                ],
                "summary": "Based on 20 verified records..."
            }
        """
        try:
            bf = self._get_bettafish_client()
            
            # Get optimized keywords
            opt_result = self.optimize_keywords(query)
            keywords = opt_result.get("keywords", [query])
            
            # Search with record IDs
            all_citations = []
            seen_ids = set()
            
            for keyword in keywords[:5]:
                results = bf.search_topics(
                    keyword=keyword,
                    hours=hours,
                    limit=limit
                )
                
                for r in results:
                    record_id = r.get('id')
                    if record_id and record_id not in seen_ids:
                        seen_ids.add(record_id)
                        all_citations.append({
                            "id": str(record_id),
                            "platform": r.get('platform', 'unknown'),
                            "title": r.get('title', '')[:100],
                            "content_preview": r.get('desc', '')[:200],
                            "author": r.get('author', ''),
                            "likes": r.get('likes', 0),
                            "created_at": r.get('created_at', '')
                        })
            
            # Sort by engagement
            all_citations.sort(key=lambda x: x.get('likes', 0), reverse=True)
            citations = all_citations[:limit]
            
            # Generate grounded summary
            summary = self._generate_grounded_summary(citations)
            
            logger.info(f"Found {len(citations)} citable records for '{query}'")
            
            return {
                "success": True,
                "query": query,
                "citation_count": len(citations),
                "citations": citations,
                "summary": summary
            }
            
        except Exception as e:
            logger.error(f"Citation search failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "citations": []
            }
    
    def _generate_grounded_summary(self, citations: List[Dict]) -> str:
        """Generate a summary that's grounded in citations."""
        if not citations:
            return "无可引用的数据记录。"
        
        lines = [
            f"基于 {len(citations)} 条数据库验证记录的分析:",
            ""
        ]
        
        # Group by platform
        platforms = {}
        for c in citations:
            platform = c.get('platform', 'unknown')
            if platform not in platforms:
                platforms[platform] = []
            platforms[platform].append(c)
        
        for platform, items in platforms.items():
            lines.append(f"**{platform}** ({len(items)} 条记录):")
            for item in items[:3]:
                lines.append(f"  - [{item['id']}] {item['title'][:50]}...")
        
        lines.append("")
        lines.append("每条记录均可通过ID在数据库中验证。")
        
        return "\n".join(lines)
    
    def verify_citation(self, record_id: str, platform: str) -> Dict:
        """
        Verify a specific citation exists in the database.
        
        Use this to validate claims made by LLMs.
        
        Args:
            record_id: Database record ID
            platform: Platform name
            
        Returns:
            Record details if found, error if not
        """
        try:
            bf = self._get_bettafish_client()
            cco = bf.get_topic_cco(record_id, platform)
            
            if cco and cco.get('title'):
                return {
                    "verified": True,
                    "record_id": record_id,
                    "platform": platform,
                    "title": cco.get('title'),
                    "author": cco.get('author'),
                    "content": cco.get('desc', '')[:500]
                }
            else:
                return {
                    "verified": False,
                    "error": f"Record {record_id} not found"
                }
                
        except Exception as e:
            return {
                "verified": False,
                "error": str(e)
            }


# Singleton
_engine: Optional[InsightEngineWrapper] = None


def get_insight_engine() -> InsightEngineWrapper:
    """Get or create the InsightEngine wrapper singleton."""
    global _engine
    if _engine is None:
        _engine = InsightEngineWrapper()
    return _engine
