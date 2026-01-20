# -*- coding: utf-8 -*-
"""
OpenNotebook Client for Perception Layer
=========================================
REST API client for open-notebook knowledge base.

Uses open-notebook for:
- Storing curated documents and research materials
- RAG-based topic generation from knowledge
- Extracting insights for content creation

API Reference: https://github.com/lfnovo/open-notebook/blob/main/docs/advanced-topics/rest-api-reference.md
"""

import os
import logging
from typing import Dict, List, Optional, Any

import httpx

logger = logging.getLogger("OpenNotebookClient")


class OpenNotebookClient:
    """
    Client for open-notebook REST API.
    
    Usage:
        client = get_open_notebook_client()
        notebooks = await client.list_notebooks()
        topics = await client.generate_topics(notebook_id)
    """
    
    def __init__(self):
        self.base_url = os.getenv("OPEN_NOTEBOOK_URL", "http://open-notebook:5055")
        self.password = os.getenv("OPEN_NOTEBOOK_PASSWORD", "")
        logger.info(f"OpenNotebookClient configured: {self.base_url}")
    
    def _headers(self) -> Dict[str, str]:
        """Get request headers with optional auth."""
        headers = {"Content-Type": "application/json"}
        if self.password:
            headers["Authorization"] = f"Bearer {self.password}"
        return headers
    
    async def list_notebooks(self) -> List[Dict[str, Any]]:
        """
        List all notebooks.
        
        Returns:
            List of notebooks: [{"id": "...", "title": "...", ...}, ...]
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/api/notebooks",
                    headers=self._headers()
                )
                
                if response.status_code != 200:
                    logger.error(f"List notebooks failed: {response.status_code}")
                    return []
                
                return response.json()
                
        except Exception as e:
            logger.error(f"List notebooks error: {e}")
            return []
    
    async def get_notebook(self, notebook_id: str) -> Optional[Dict[str, Any]]:
        """Get notebook details by ID."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/api/notebooks/{notebook_id}",
                    headers=self._headers()
                )
                
                if response.status_code != 200:
                    return None
                
                return response.json()
                
        except Exception as e:
            logger.error(f"Get notebook error: {e}")
            return None
    
    async def list_sources(self, notebook_id: str) -> List[Dict[str, Any]]:
        """
        List all sources in a notebook.
        
        Returns:
            List of sources (documents, URLs, etc.)
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/api/notebooks/{notebook_id}/sources",
                    headers=self._headers()
                )
                
                if response.status_code != 200:
                    return []
                
                return response.json()
                
        except Exception as e:
            logger.error(f"List sources error: {e}")
            return []
    
    async def chat(
        self,
        notebook_id: str,
        query: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Chat with a notebook using RAG.
        
        Args:
            notebook_id: Notebook to query
            query: User question
            session_id: Optional session for context continuity
            
        Returns:
            {"response": "...", "sources": [...]}
        """
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                payload = {"query": query}
                if session_id:
                    payload["session_id"] = session_id
                
                response = await client.post(
                    f"{self.base_url}/api/notebooks/{notebook_id}/chat",
                    json=payload,
                    headers=self._headers()
                )
                
                if response.status_code != 200:
                    logger.error(f"Chat failed: {response.text}")
                    return {"error": response.text}
                
                return response.json()
                
        except Exception as e:
            logger.error(f"Chat error: {e}")
            return {"error": str(e)}
    
    async def generate_topics(
        self,
        notebook_id: str,
        count: int = 5,
        style: str = "social_media"
    ) -> List[Dict[str, Any]]:
        """
        Generate topic suggestions from notebook knowledge.
        
        Args:
            notebook_id: Notebook to extract from
            count: Number of topics to generate
            style: Content style (social_media, educational, news)
            
        Returns:
            List of topic suggestions with title, key_points, etc.
        """
        prompt = f"""
Based on the knowledge in this notebook, suggest {count} video topics 
that would educate and engage viewers on social media.

For each topic, provide in JSON format:
1. "title": Catchy, engaging title for social media
2. "key_points": Array of 3-5 key points to cover
3. "target_audience": Who this content is for
4. "content_angle": Unique perspective or hook
5. "estimated_duration": Suggested video length

Return ONLY a JSON array, no other text.
"""
        
        result = await self.chat(notebook_id, prompt)
        
        if "error" in result:
            return []
        
        # Parse response
        try:
            import json
            response_text = result.get("response", "")
            
            # Try to extract JSON from response
            if "[" in response_text:
                json_start = response_text.index("[")
                json_end = response_text.rindex("]") + 1
                topics = json.loads(response_text[json_start:json_end])
                return topics
            
            return []
            
        except Exception as e:
            logger.error(f"Parse topics error: {e}")
            return []
    
    def is_available(self) -> bool:
        """Check if open-notebook is reachable."""
        import requests
        try:
            response = requests.get(f"{self.base_url}/api/notebooks", timeout=5)
            return response.status_code in [200, 401]  # 401 means auth required but reachable
        except Exception:
            return False
    
    # =========================================================================
    # Perception Layer v3.0: Enhanced Knowledge Base Methods
    # =========================================================================
    
    async def ask(
        self,
        notebook_id: str,
        question: str,
        mode: str = "ask"
    ) -> Dict[str, Any]:
        """
        Ask a question using RAG (Retrieval-Augmented Generation).
        
        Different from chat(): ask() uses vector search strategy first,
        then synthesizes answer from retrieved chunks.
        
        Args:
            notebook_id: Notebook to query
            question: Question to answer
            mode: "ask" (RAG) or "chat" (full context)
            
        Returns:
            {
                "response": "Answer text",
                "sources": [{"title": "...", "excerpt": "...", "score": 0.95}],
                "notebook_id": "..."
            }
        """
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                payload = {
                    "query": question,
                    "mode": mode  # "ask" uses RAG strategy
                }
                
                response = await client.post(
                    f"{self.base_url}/api/notebooks/{notebook_id}/ask",
                    json=payload,
                    headers=self._headers()
                )
                
                if response.status_code != 200:
                    # Fallback to chat endpoint if ask not available
                    logger.warning(f"Ask endpoint not available, falling back to chat")
                    return await self.chat(notebook_id, question)
                
                result = response.json()
                result["notebook_id"] = notebook_id
                return result
                
        except Exception as e:
            logger.error(f"Ask error: {e}")
            return {"error": str(e)}
    
    async def transform(
        self,
        notebook_id: str,
        template: str,
        source_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Apply a transformation template to sources in batch.
        
        Templates like "视频选题生成", "人物分析", "章节摘要" are applied
        to each source, producing structured output.
        
        Args:
            notebook_id: Notebook containing sources
            template: Transformation template/prompt
            source_ids: Optional specific sources to transform (all if None)
            
        Returns:
            List of transformed outputs, one per source
        """
        # Get sources first
        sources = await self.list_sources(notebook_id)
        
        if source_ids:
            sources = [s for s in sources if s.get("id") in source_ids]
        
        if not sources:
            logger.warning(f"No sources found in notebook {notebook_id}")
            return []
        
        results = []
        
        for source in sources:
            source_id = source.get("id", "")
            source_title = source.get("title", source.get("name", "Unknown"))
            
            # Create prompt with source context
            prompt = f"""Apply this transformation to the source:

TEMPLATE: {template}

SOURCE: {source_title}
{source.get('content', source.get('excerpt', ''))[:3000]}

Return structured JSON output."""
            
            try:
                response = await self.chat(notebook_id, prompt)
                
                if "error" not in response:
                    results.append({
                        "source_id": source_id,
                        "source_title": source_title,
                        "template": template,
                        "output": response.get("response", ""),
                        "success": True
                    })
                else:
                    results.append({
                        "source_id": source_id,
                        "source_title": source_title,
                        "error": response.get("error"),
                        "success": False
                    })
                    
            except Exception as e:
                logger.error(f"Transform error for {source_id}: {e}")
                results.append({
                    "source_id": source_id,
                    "source_title": source_title,
                    "error": str(e),
                    "success": False
                })
        
        logger.info(f"Transformed {len([r for r in results if r.get('success')])} sources")
        return results
    
    async def get_curriculum_progress(
        self,
        artist_id: str,
        notebook_id: str
    ) -> Dict[str, Any]:
        """
        Get curriculum progress for an artist's knowledge base.
        
        Retrieves sources from notebook and maps against Sanity's
        curriculumProgress to determine what's been covered.
        
        Args:
            artist_id: Sanity artist document ID
            notebook_id: Open Notebook ID
            
        Returns:
            {
                "total_sources": 10,
                "completed": 3,
                "in_progress": 1,
                "pending": 6,
                "next_chapter": {"id": "...", "title": "..."},
                "progress_percent": 30
            }
        """
        # Get all sources from notebook
        sources = await self.list_sources(notebook_id)
        
        # Get artist curriculum progress from Sanity
        from lib.sanity_client import get_sanity_client
        sanity = get_sanity_client()
        
        try:
            artist = sanity.client.get_document(artist_id)
            if not artist:
                return {"error": f"Artist {artist_id} not found"}
            
            curriculum = artist.get("knowledgeBase", {}).get("curriculumProgress", [])
            
            # Count statuses
            completed_ids = [c["chapterId"] for c in curriculum if c.get("status") == "completed"]
            in_progress_ids = [c["chapterId"] for c in curriculum if c.get("status") == "in_progress"]
            
            total = len(sources)
            completed = len([s for s in sources if s.get("id") in completed_ids])
            in_progress = len([s for s in sources if s.get("id") in in_progress_ids])
            pending = total - completed - in_progress
            
            # Find next chapter (first pending source)
            next_chapter = None
            for source in sources:
                if source.get("id") not in completed_ids and source.get("id") not in in_progress_ids:
                    next_chapter = {
                        "id": source.get("id"),
                        "title": source.get("title", source.get("name", "Unknown"))
                    }
                    break
            
            return {
                "artist_id": artist_id,
                "notebook_id": notebook_id,
                "total_sources": total,
                "completed": completed,
                "in_progress": in_progress,
                "pending": pending,
                "next_chapter": next_chapter,
                "progress_percent": round((completed / max(total, 1)) * 100, 1)
            }
            
        except Exception as e:
            logger.error(f"Get curriculum progress error: {e}")
            return {"error": str(e)}


# =========================================================================
# Singleton
# =========================================================================

_client: Optional[OpenNotebookClient] = None


def get_open_notebook_client() -> OpenNotebookClient:
    """Get or create the OpenNotebook client singleton."""
    global _client
    if _client is None:
        _client = OpenNotebookClient()
    return _client
