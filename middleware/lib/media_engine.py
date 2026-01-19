# -*- coding: utf-8 -*-
"""
MediaEngine Integration
=======================
Wrapper for BettaFish MediaEngine providing Bocha AI multimodal search.

Key Features:
- AI-generated summaries for search results
- Modal cards for structured data (weather, stocks, etc.)
- Follow-up question suggestions
- Time-filtered search (24h, week)

Usage:
    from lib.media_engine import get_media_engine
    
    me = get_media_engine()
    
    # Comprehensive multimodal search
    results = me.search("AI技术发展趋势")
    
    # Get structured data (weather, stocks, etc.)
    data = me.search_structured("上海天气")
    
    # Fast web-only search
    pages = me.search_web_only("Python教程")
"""

import logging
import sys
import os
from typing import Dict, List, Optional, Any

logger = logging.getLogger("MediaEngine")

# Add BettaFish to path
BETTAFISH_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../external/BettaFish')
)


class MediaEngineWrapper:
    """
    Wrapper for BettaFish MediaEngine (Bocha AI Search).
    
    Provides:
    - Multimodal web search with AI summaries
    - Structured data queries (weather, stocks, etc.)
    - Time-filtered news search
    - Follow-up suggestions
    """
    
    def __init__(self):
        """Initialize MediaEngine wrapper."""
        self._bocha_client = None
        logger.info("MediaEngineWrapper initialized")
    
    def _get_bocha_client(self):
        """Lazy load Bocha client."""
        if self._bocha_client is None:
            # Load BettaFish .env
            from dotenv import load_dotenv
            bettafish_env = os.path.join(BETTAFISH_PATH, '.env')
            if os.path.exists(bettafish_env):
                load_dotenv(bettafish_env)
                logger.info(f"Loaded BettaFish config from {bettafish_env}")
            
            if BETTAFISH_PATH not in sys.path:
                sys.path.insert(0, BETTAFISH_PATH)
            
            try:
                from MediaEngine.tools.search import BochaMultimodalSearch
                self._bocha_client = BochaMultimodalSearch()
                logger.info("BochaMultimodalSearch loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load BochaMultimodalSearch: {e}")
                raise
        return self._bocha_client
    
    def _response_to_dict(self, response) -> Dict:
        """Convert BochaResponse to dict."""
        return {
            "query": response.query,
            "conversation_id": response.conversation_id,
            "answer": response.answer,  # AI-generated summary
            "follow_ups": response.follow_ups,  # Suggested follow-up questions
            "webpages": [
                {
                    "title": w.name,
                    "url": w.url,
                    "snippet": w.snippet,
                    "display_url": w.display_url,
                    "date": w.date_last_crawled
                }
                for w in response.webpages
            ],
            "images": [
                {
                    "name": img.name,
                    "url": img.content_url,
                    "thumbnail": img.thumbnail_url,
                    "width": img.width,
                    "height": img.height
                }
                for img in response.images
            ],
            "modal_cards": [
                {
                    "type": card.card_type,
                    "content": card.content
                }
                for card in response.modal_cards
            ],
            "webpage_count": len(response.webpages),
            "image_count": len(response.images),
            "card_count": len(response.modal_cards)
        }
    
    def search(self, query: str, max_results: int = 10) -> Dict:
        """
        Comprehensive multimodal search with AI summary.
        
        Returns webpages, images, AI summary, and follow-up suggestions.
        
        Args:
            query: Search query
            max_results: Maximum webpage results
            
        Returns:
            Dict with webpages, images, answer, follow_ups, modal_cards
        """
        try:
            client = self._get_bocha_client()
            response = client.comprehensive_search(query, max_results=max_results)
            result = self._response_to_dict(response)
            logger.info(f"Search '{query}': {result['webpage_count']} pages, {result['image_count']} images, answer: {bool(result['answer'])}")
            return {"success": True, **result}
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return {"success": False, "error": str(e), "query": query}
    
    def search_web_only(self, query: str, max_results: int = 15) -> Dict:
        """
        Fast web-only search without AI summary.
        
        Faster and cheaper than comprehensive search.
        
        Args:
            query: Search query
            max_results: Maximum results
            
        Returns:
            Dict with webpages only
        """
        try:
            client = self._get_bocha_client()
            response = client.web_search_only(query, max_results=max_results)
            result = self._response_to_dict(response)
            logger.info(f"Web search '{query}': {result['webpage_count']} pages")
            return {"success": True, **result}
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return {"success": False, "error": str(e), "query": query}
    
    def search_structured(self, query: str) -> Dict:
        """
        Search for structured data (weather, stocks, etc.).
        
        Triggers modal cards for supported query types:
        - Weather: "上海天气"
        - Stocks: "东方财富股票"
        - Currency: "美元汇率"
        - Wikipedia: "什么是人工智能"
        
        Args:
            query: Structured data query
            
        Returns:
            Dict with modal_cards containing structured data
        """
        try:
            client = self._get_bocha_client()
            response = client.search_for_structured_data(query)
            result = self._response_to_dict(response)
            logger.info(f"Structured search '{query}': {result['card_count']} cards")
            return {"success": True, **result}
        except Exception as e:
            logger.error(f"Structured search failed: {e}")
            return {"success": False, "error": str(e), "query": query}
    
    def search_last_24h(self, query: str) -> Dict:
        """
        Search for content from the last 24 hours.
        
        Good for breaking news and trending topics.
        
        Args:
            query: Search query
            
        Returns:
            Dict with recent results
        """
        try:
            client = self._get_bocha_client()
            response = client.search_last_24_hours(query)
            result = self._response_to_dict(response)
            logger.info(f"24h search '{query}': {result['webpage_count']} pages")
            return {"success": True, **result}
        except Exception as e:
            logger.error(f"24h search failed: {e}")
            return {"success": False, "error": str(e), "query": query}
    
    def search_last_week(self, query: str) -> Dict:
        """
        Search for content from the last week.
        
        Good for weekly roundups and trend analysis.
        
        Args:
            query: Search query
            
        Returns:
            Dict with weekly results
        """
        try:
            client = self._get_bocha_client()
            response = client.search_last_week(query)
            result = self._response_to_dict(response)
            logger.info(f"Week search '{query}': {result['webpage_count']} pages")
            return {"success": True, **result}
        except Exception as e:
            logger.error(f"Week search failed: {e}")
            return {"success": False, "error": str(e), "query": query}
    
    def get_ai_summary(self, query: str) -> str:
        """
        Get just the AI-generated summary for a query.
        
        Args:
            query: Search query
            
        Returns:
            AI-generated summary string
        """
        result = self.search(query, max_results=5)
        return result.get("answer", "")
    
    def get_follow_up_questions(self, query: str) -> List[str]:
        """
        Get AI-suggested follow-up questions for a query.
        
        Args:
            query: Search query
            
        Returns:
            List of suggested follow-up questions
        """
        result = self.search(query, max_results=5)
        follow_ups = result.get("follow_ups", [])
        # Flatten nested lists if present
        flat = []
        for item in follow_ups:
            if isinstance(item, list):
                flat.extend(item)
            else:
                flat.append(item)
        return flat
    
    def deep_research(self, query: str, save_report: bool = False) -> Dict:
        """
        Run full deep research with BettaFish MediaEngine's DeepSearchAgent.
        
        This implements the COMPLETE BettaFish workflow:
        1. Generate report structure (LLM plans paragraphs)
        2. For each paragraph:
           - Initial Bocha multimodal search + summary
           - Reflection loop × N (refine search, improve summary)
        3. Generate final report
        
        Uses Antigravity Manager (zero LLM cost).
        
        Args:
            query: Research query (e.g., "人工智能商业应用趋势")
            save_report: Whether to save report to file
            
        Returns:
            {
                "success": True,
                "query": "...",
                "report": "Final report markdown...",
                "paragraphs": N
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
            
            # Import and run the full DeepSearchAgent (MediaEngine version)
            from MediaEngine.agent import DeepSearchAgent
            
            logger.info(f"Starting MediaEngine deep research: {query}")
            agent = DeepSearchAgent()
            
            # Run the full research workflow
            report = agent.research(query, save_report=save_report)
            
            # Get progress stats
            stats = agent.get_progress_summary()
            
            logger.info(f"MediaEngine deep research complete for: {query}")
            
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
            logger.error(f"MediaEngine deep research failed: {e}\n{traceback.format_exc()}")
            return {
                "success": False,
                "query": query,
                "error": str(e)
            }


# Singleton
_engine: Optional[MediaEngineWrapper] = None


def get_media_engine() -> MediaEngineWrapper:
    """Get or create the MediaEngine wrapper singleton."""
    global _engine
    if _engine is None:
        _engine = MediaEngineWrapper()
    return _engine
