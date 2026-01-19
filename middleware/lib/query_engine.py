# -*- coding: utf-8 -*-
"""
QueryEngine Integration
=======================
Wrapper for BettaFish QueryEngine providing web/news search via Tavily API.

Key Features:
- News search with time filters (24h, week, date range)
- Image search for B-roll content
- Deep news analysis with AI summaries
- Complements InsightEngine (social media) with web context

Usage:
    from lib.query_engine import get_query_engine
    
    qe = get_query_engine()
    
    # Basic news search
    news = qe.search_news("AI发展趋势")
    
    # Get latest breaking news
    breaking = qe.search_last_24h("OpenAI发布")
    
    # Find images for B-roll
    images = qe.search_images("人工智能机器人")
"""

import logging
import sys
import os
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger("QueryEngine")

# Add BettaFish to path
BETTAFISH_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../external/BettaFish')
)


class QueryEngineWrapper:
    """
    Wrapper for BettaFish QueryEngine (Tavily-based web search).
    
    Provides:
    - Web/news search
    - Time-filtered search (24h, week, date range)
    - Image search for B-roll
    - Deep news analysis
    """
    
    def __init__(self):
        """Initialize QueryEngine wrapper."""
        self._tavily_client = None
        logger.info("QueryEngineWrapper initialized")
    
    def _get_tavily_client(self):
        """Lazy load Tavily client."""
        if self._tavily_client is None:
            # Load BettaFish .env
            from dotenv import load_dotenv
            bettafish_env = os.path.join(BETTAFISH_PATH, '.env')
            if os.path.exists(bettafish_env):
                load_dotenv(bettafish_env)
                logger.info(f"Loaded BettaFish config from {bettafish_env}")
            
            if BETTAFISH_PATH not in sys.path:
                sys.path.insert(0, BETTAFISH_PATH)
            
            try:
                from QueryEngine.tools.search import TavilyNewsAgency
                self._tavily_client = TavilyNewsAgency()
                logger.info("TavilyNewsAgency loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load TavilyNewsAgency: {e}")
                raise
        return self._tavily_client
    
    def _response_to_dict(self, response) -> Dict:
        """Convert TavilyResponse to dict."""
        return {
            "query": response.query,
            "answer": response.answer,
            "results": [
                {
                    "title": r.title,
                    "url": r.url,
                    "content": r.content[:500] if r.content else "",
                    "score": r.score,
                    "published_date": r.published_date
                }
                for r in response.results
            ],
            "images": [
                {
                    "url": img.url,
                    "description": img.description
                }
                for img in response.images
            ],
            "response_time": response.response_time,
            "result_count": len(response.results)
        }
    
    def search_news(self, query: str, max_results: int = 7) -> Dict:
        """
        Basic news search.
        
        Args:
            query: Search query
            max_results: Maximum results (default 7)
            
        Returns:
            Dict with results, answer (if available), and metadata
        """
        try:
            client = self._get_tavily_client()
            response = client.basic_search_news(query, max_results=max_results)
            result = self._response_to_dict(response)
            logger.info(f"News search '{query}': {result['result_count']} results")
            return result
        except Exception as e:
            logger.error(f"News search failed: {e}")
            return {"error": str(e), "results": [], "query": query}
    
    def deep_search(self, query: str) -> Dict:
        """
        Deep news analysis with AI summary.
        
        Returns up to 20 results with an AI-generated summary.
        
        Args:
            query: Search query
            
        Returns:
            Dict with results, AI answer, and metadata
        """
        try:
            client = self._get_tavily_client()
            response = client.deep_search_news(query)
            result = self._response_to_dict(response)
            logger.info(f"Deep search '{query}': {result['result_count']} results, answer: {bool(result['answer'])}")
            return result
        except Exception as e:
            logger.error(f"Deep search failed: {e}")
            return {"error": str(e), "results": [], "query": query}
    
    def search_last_24h(self, query: str) -> Dict:
        """
        Search news from the last 24 hours.
        
        Good for breaking news and trending topics.
        
        Args:
            query: Search query
            
        Returns:
            Dict with recent news results
        """
        try:
            client = self._get_tavily_client()
            response = client.search_news_last_24_hours(query)
            result = self._response_to_dict(response)
            logger.info(f"24h search '{query}': {result['result_count']} results")
            return result
        except Exception as e:
            logger.error(f"24h search failed: {e}")
            return {"error": str(e), "results": [], "query": query}
    
    def search_last_week(self, query: str) -> Dict:
        """
        Search news from the last week.
        
        Good for weekly roundups and trend analysis.
        
        Args:
            query: Search query
            
        Returns:
            Dict with weekly news results
        """
        try:
            client = self._get_tavily_client()
            response = client.search_news_last_week(query)
            result = self._response_to_dict(response)
            logger.info(f"Week search '{query}': {result['result_count']} results")
            return result
        except Exception as e:
            logger.error(f"Week search failed: {e}")
            return {"error": str(e), "results": [], "query": query}
    
    def search_images(self, query: str) -> Dict:
        """
        Search for images related to a topic.
        
        Useful for finding B-roll images for video production.
        
        Args:
            query: Search query
            
        Returns:
            Dict with image URLs and descriptions
        """
        try:
            client = self._get_tavily_client()
            response = client.search_images_for_news(query)
            result = self._response_to_dict(response)
            logger.info(f"Image search '{query}': {len(result['images'])} images")
            return result
        except Exception as e:
            logger.error(f"Image search failed: {e}")
            return {"error": str(e), "images": [], "query": query}
    
    def search_by_date_range(
        self, 
        query: str, 
        start_date: str, 
        end_date: str
    ) -> Dict:
        """
        Search news within a specific date range.
        
        Args:
            query: Search query
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            Dict with results from date range
        """
        try:
            client = self._get_tavily_client()
            response = client.search_news_by_date(query, start_date, end_date)
            result = self._response_to_dict(response)
            logger.info(f"Date range search '{query}' ({start_date} to {end_date}): {result['result_count']} results")
            return result
        except Exception as e:
            logger.error(f"Date range search failed: {e}")
            return {"error": str(e), "results": [], "query": query}
    
    def get_context_for_topic(self, topic_title: str) -> Dict:
        """
        Get comprehensive web context for a social media topic.
        
        Combines:
        - Quick news search
        - Image search for B-roll
        
        Useful for enriching InsightEngine data with external context.
        
        Args:
            topic_title: Title of the topic
            
        Returns:
            Dict with news context and images
        """
        news = self.search_news(topic_title, max_results=5)
        images = self.search_images(topic_title)
        
        return {
            "topic": topic_title,
            "news": news.get("results", []),
            "news_count": news.get("result_count", 0),
            "images": images.get("images", []),
            "image_count": len(images.get("images", [])),
            "has_context": news.get("result_count", 0) > 0
        }
    
    def deep_research(self, query: str, save_report: bool = False) -> Dict:
        """
        Run full deep research with BettaFish QueryEngine's DeepSearchAgent.
        
        This implements the COMPLETE BettaFish workflow:
        1. Generate report structure (LLM plans paragraphs)
        2. For each paragraph:
           - Initial Tavily search + summary
           - Reflection loop × N (refine search, improve summary)
        3. Generate final report
        
        Uses Antigravity Manager (zero LLM cost).
        
        Args:
            query: Research query (e.g., "AI技术发展趋势分析")
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
            
            # Import and run the full DeepSearchAgent (QueryEngine version)
            from QueryEngine.agent import DeepSearchAgent
            
            logger.info(f"Starting QueryEngine deep research: {query}")
            agent = DeepSearchAgent()
            
            # Run the full research workflow
            report = agent.research(query, save_report=save_report)
            
            # Get progress stats
            stats = agent.get_progress_summary()
            
            logger.info(f"QueryEngine deep research complete for: {query}")
            
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
            logger.error(f"QueryEngine deep research failed: {e}\n{traceback.format_exc()}")
            return {
                "success": False,
                "query": query,
                "error": str(e)
            }
_engine: Optional[QueryEngineWrapper] = None


def get_query_engine() -> QueryEngineWrapper:
    """Get or create the QueryEngine wrapper singleton."""
    global _engine
    if _engine is None:
        _engine = QueryEngineWrapper()
    return _engine
