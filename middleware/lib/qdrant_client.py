# -*- coding: utf-8 -*-
"""
QdrantClient for Perception Layer
=================================
Vector database client for semantic deduplication of topics.

Uses Qdrant for:
- Storing topic embeddings
- Finding semantically similar topics (deduplication)
- Time-windowed similarity queries

Embedding model: Uses Ollama's nomic-embed-text or OpenAI-compatible embedding API
"""

import os
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

logger = logging.getLogger("QdrantClient")

# Qdrant Python client
try:
    from qdrant_client import QdrantClient as QdrantSDK
    from qdrant_client.models import (
        Distance, VectorParams, PointStruct, 
        Filter, FieldCondition, Range, MatchValue
    )
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    QdrantSDK = Any  # Type stub for when qdrant-client not installed
    logger.warning("qdrant-client not installed. Run: pip install qdrant-client")


class PerceptionQdrantClient:
    """
    Qdrant client for topic semantic deduplication.
    
    Usage:
        client = get_qdrant_client()
        
        # Store topic embedding
        client.upsert_topic(topic_id, title, content)
        
        # Find similar topics
        similar = client.find_similar(title, content, threshold=0.85)
    """
    
    COLLECTION_NAME = "perception_topics"
    EMBEDDING_DIM = 768  # nomic-embed-text dimension
    
    def __init__(self):
        self.qdrant_url = os.getenv("QDRANT_URL", "http://qdrant:6333")
        self.ollama_url = os.getenv("OLLAMA_URL", "http://ollama:11434")
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
        
        self._client: Optional[QdrantSDK] = None
        self._initialized = False
        
        logger.info(f"PerceptionQdrantClient configured: {self.qdrant_url}")
    
    @property
    def client(self) -> QdrantSDK:
        """Lazy-load Qdrant client."""
        if not QDRANT_AVAILABLE:
            raise RuntimeError("qdrant-client not installed")
        
        if self._client is None:
            # Parse URL for host and port
            url = self.qdrant_url.replace("http://", "").replace("https://", "")
            host = url.split(":")[0]
            port = int(url.split(":")[1]) if ":" in url else 6333
            
            self._client = QdrantSDK(host=host, port=port)
            self._ensure_collection()
        
        return self._client
    
    def _ensure_collection(self):
        """Create collection if it doesn't exist."""
        if self._initialized:
            return
            
        collections = self.client.get_collections().collections
        exists = any(c.name == self.COLLECTION_NAME for c in collections)
        
        if not exists:
            logger.info(f"Creating Qdrant collection: {self.COLLECTION_NAME}")
            self.client.create_collection(
                collection_name=self.COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=self.EMBEDDING_DIM,
                    distance=Distance.COSINE
                )
            )
        
        self._initialized = True
    
    async def get_embedding(self, text: str) -> List[float]:
        """Get embedding from Ollama."""
        import httpx
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.ollama_url}/api/embeddings",
                json={
                    "model": self.embedding_model,
                    "prompt": text[:2000]  # Limit text length
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Embedding failed: {response.text}")
                raise RuntimeError(f"Embedding API error: {response.status_code}")
            
            result = response.json()
            return result.get("embedding", [])
    
    async def upsert_topic(
        self,
        topic_id: str,
        title: str,
        content: str,
        source_type: str = "unknown",
        created_at: Optional[datetime] = None
    ) -> bool:
        """
        Store or update topic embedding in Qdrant.
        
        Args:
            topic_id: Sanity document ID
            title: Topic title
            content: Topic content/snippet
            source_type: social_crawler, knowledge_base, rss_feed, manual
            created_at: Topic creation time (for time-windowed queries)
            
        Returns:
            True if successful
        """
        try:
            # Generate embedding from title + content
            text = f"{title}\n\n{content[:500]}"
            embedding = await self.get_embedding(text)
            
            if not embedding:
                logger.warning(f"Empty embedding for topic {topic_id}")
                return False
            
            # Create point ID from topic_id hash
            point_id = int(hashlib.md5(topic_id.encode()).hexdigest()[:16], 16)
            
            # Store with metadata
            self.client.upsert(
                collection_name=self.COLLECTION_NAME,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload={
                            "topic_id": topic_id,
                            "title": title,
                            "source_type": source_type,
                            "created_at": (created_at or datetime.utcnow()).isoformat()
                        }
                    )
                ]
            )
            
            logger.info(f"Stored embedding for topic: {topic_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upsert topic {topic_id}: {e}")
            return False
    
    async def find_similar(
        self,
        title: str,
        content: str,
        threshold: float = 0.85,
        time_window_hours: int = 72,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find similar topics using vector similarity.
        
        Args:
            title: Topic title to search for
            content: Topic content to search for
            threshold: Minimum similarity score (0-1)
            time_window_hours: Only search topics from last N hours
            limit: Maximum results to return
            
        Returns:
            List of similar topics with scores:
            [{"topic_id": "...", "title": "...", "score": 0.92}, ...]
        """
        try:
            # Generate embedding for query
            text = f"{title}\n\n{content[:500]}"
            query_embedding = await self.get_embedding(text)
            
            if not query_embedding:
                return []
            
            # Check if collection has any points
            try:
                info = self.client.get_collection(self.COLLECTION_NAME)
                if info.points_count == 0:
                    logger.info("Collection is empty, no similar topics to find")
                    return []
            except Exception:
                return []
            
            # Build time filter
            cutoff_time = (datetime.utcnow() - timedelta(hours=time_window_hours)).isoformat()
            
            # Query using query_points (qdrant-client v1.7+)
            from qdrant_client.models import QueryRequest
            
            results = self.client.query_points(
                collection_name=self.COLLECTION_NAME,
                query=query_embedding,
                limit=limit,
                score_threshold=threshold,
                with_payload=True
            )
            
            # Format results
            similar = []
            for point in results.points:
                # Check time filter manually (simpler than query filter)
                created_at = point.payload.get("created_at", "")
                if created_at >= cutoff_time:
                    similar.append({
                        "topic_id": point.payload.get("topic_id"),
                        "title": point.payload.get("title"),
                        "source_type": point.payload.get("source_type"),
                        "score": point.score,
                        "created_at": created_at
                    })
            
            logger.info(f"Found {len(similar)} similar topics for '{title[:30]}...'")
            return similar
            
        except Exception as e:
            logger.error(f"Similarity search failed: {e}")
            return []
    
    def delete_topic(self, topic_id: str) -> bool:
        """Delete a topic from the vector store."""
        try:
            point_id = int(hashlib.md5(topic_id.encode()).hexdigest()[:16], 16)
            self.client.delete(
                collection_name=self.COLLECTION_NAME,
                points_selector=[point_id]
            )
            return True
        except Exception as e:
            logger.error(f"Failed to delete topic {topic_id}: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        try:
            info = self.client.get_collection(self.COLLECTION_NAME)
            return {
                "collection": self.COLLECTION_NAME,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "status": info.status.name
            }
        except Exception as e:
            return {"error": str(e)}
    
    # =========================================================================
    # Hybrid Search with RRF (Perception Layer v3.0)
    # =========================================================================
    
    async def hybrid_search(
        self,
        query: str,
        limit: int = 10,
        vector_weight: float = 0.6,
        keyword_weight: float = 0.4,
        time_window_hours: int = 72,
        rrf_k: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search combining vector similarity and keyword matching using RRF.
        
        RRF (Reciprocal Rank Fusion) combines results from multiple retrieval
        methods to improve precision over either method alone.
        
        Formula: RRF_score = Σ (1 / (k + rank_i))
        
        Args:
            query: Search query text
            limit: Maximum results to return
            vector_weight: Weight for vector results (0-1)
            keyword_weight: Weight for keyword results (0-1)
            time_window_hours: Only search recent topics
            rrf_k: RRF constant (higher = less penalty for lower ranks)
            
        Returns:
            List of topics sorted by fused RRF score
        """
        logger.info(f"Hybrid search: '{query[:50]}...' (v={vector_weight}, k={keyword_weight})")
        
        # Get vector results
        vector_results = await self._vector_search(query, limit * 2, time_window_hours)
        
        # Get keyword results
        keyword_results = await self._keyword_search(query, limit * 2, time_window_hours)
        
        # Fuse results using RRF
        fused = self._rrf_fusion(
            vector_results, 
            keyword_results,
            vector_weight,
            keyword_weight,
            rrf_k
        )
        
        # Return top results
        sorted_results = sorted(fused.values(), key=lambda x: x["rrf_score"], reverse=True)
        
        logger.info(f"Hybrid search returned {len(sorted_results[:limit])} results")
        return sorted_results[:limit]
    
    async def _vector_search(
        self,
        query: str,
        limit: int,
        time_window_hours: int
    ) -> List[Dict[str, Any]]:
        """Vector-only search using embeddings."""
        try:
            query_embedding = await self.get_embedding(query)
            
            if not query_embedding:
                return []
            
            cutoff_time = (datetime.utcnow() - timedelta(hours=time_window_hours)).isoformat()
            
            results = self.client.query_points(
                collection_name=self.COLLECTION_NAME,
                query=query_embedding,
                limit=limit,
                with_payload=True
            )
            
            ranked = []
            for rank, point in enumerate(results.points, 1):
                created_at = point.payload.get("created_at", "")
                if created_at >= cutoff_time:
                    ranked.append({
                        "topic_id": point.payload.get("topic_id"),
                        "title": point.payload.get("title"),
                        "source_type": point.payload.get("source_type"),
                        "vector_score": point.score,
                        "vector_rank": rank,
                        "created_at": created_at
                    })
            
            return ranked
            
        except Exception as e:
            logger.warning(f"Vector search failed: {e}")
            return []
    
    async def _keyword_search(
        self,
        query: str,
        limit: int,
        time_window_hours: int
    ) -> List[Dict[str, Any]]:
        """
        Keyword-based search using payload filtering.
        
        Note: Qdrant doesn't have built-in full-text search, so we:
        1. Scroll through recent points
        2. Score by keyword overlap with title
        
        For production, consider adding Elasticsearch or Qdrant's 
        upcoming sparse vector support.
        """
        try:
            cutoff_time = (datetime.utcnow() - timedelta(hours=time_window_hours)).isoformat()
            
            # Extract keywords from query
            query_keywords = self._extract_keywords(query)
            
            if not query_keywords:
                return []
            
            # Scroll through recent points
            # Note: For large collections, add proper pagination
            scroll_result = self.client.scroll(
                collection_name=self.COLLECTION_NAME,
                limit=500,  # Reasonable limit for keyword matching
                with_payload=True
            )
            
            points = scroll_result[0]  # (points, next_offset)
            
            # Score each point by keyword overlap
            scored = []
            for point in points:
                created_at = point.payload.get("created_at", "")
                
                if created_at < cutoff_time:
                    continue
                
                title = point.payload.get("title", "")
                title_keywords = self._extract_keywords(title)
                
                # Calculate Jaccard-like overlap score
                overlap = len(query_keywords & title_keywords)
                if overlap > 0:
                    score = overlap / len(query_keywords | title_keywords)
                    scored.append({
                        "topic_id": point.payload.get("topic_id"),
                        "title": title,
                        "source_type": point.payload.get("source_type"),
                        "keyword_score": score,
                        "keyword_overlap": overlap,
                        "created_at": created_at
                    })
            
            # Sort by keyword score and assign ranks
            scored.sort(key=lambda x: x["keyword_score"], reverse=True)
            for rank, item in enumerate(scored, 1):
                item["keyword_rank"] = rank
            
            return scored[:limit]
            
        except Exception as e:
            logger.warning(f"Keyword search failed: {e}")
            return []
    
    def _extract_keywords(self, text: str) -> set:
        """Extract keywords from text (simple tokenization)."""
        import re
        
        # Remove punctuation and split
        text_lower = text.lower()
        words = re.findall(r'[\w\u4e00-\u9fff]+', text_lower)
        
        # Filter short words and stopwords
        stopwords = {'的', '是', '和', '在', '了', '有', '这', '那', '我', '你',
                     'the', 'a', 'an', 'is', 'are', 'and', 'or', 'in', 'on', 'at'}
        
        keywords = {w for w in words if len(w) >= 2 and w not in stopwords}
        return keywords
    
    def _rrf_fusion(
        self,
        vector_results: List[Dict],
        keyword_results: List[Dict],
        vector_weight: float,
        keyword_weight: float,
        k: int
    ) -> Dict[str, Dict]:
        """
        Fuse results using Reciprocal Rank Fusion (RRF).
        
        RRF formula: score = Σ weight_i * (1 / (k + rank_i))
        
        Higher k = less penalty for lower ranks (smoother fusion)
        Typical k values: 60 (default), 1-100
        """
        fused = {}
        
        # Add vector results
        for item in vector_results:
            topic_id = item["topic_id"]
            vector_rrf = vector_weight * (1.0 / (k + item.get("vector_rank", 1000)))
            
            if topic_id not in fused:
                fused[topic_id] = {
                    "topic_id": topic_id,
                    "title": item["title"],
                    "source_type": item.get("source_type"),
                    "created_at": item.get("created_at"),
                    "vector_score": item.get("vector_score", 0),
                    "vector_rank": item.get("vector_rank"),
                    "keyword_score": 0,
                    "keyword_rank": None,
                    "rrf_score": 0
                }
            
            fused[topic_id]["rrf_score"] += vector_rrf
            fused[topic_id]["vector_score"] = item.get("vector_score", 0)
            fused[topic_id]["vector_rank"] = item.get("vector_rank")
        
        # Add keyword results
        for item in keyword_results:
            topic_id = item["topic_id"]
            keyword_rrf = keyword_weight * (1.0 / (k + item.get("keyword_rank", 1000)))
            
            if topic_id not in fused:
                fused[topic_id] = {
                    "topic_id": topic_id,
                    "title": item["title"],
                    "source_type": item.get("source_type"),
                    "created_at": item.get("created_at"),
                    "vector_score": 0,
                    "vector_rank": None,
                    "keyword_score": item.get("keyword_score", 0),
                    "keyword_rank": item.get("keyword_rank"),
                    "rrf_score": 0
                }
            
            fused[topic_id]["rrf_score"] += keyword_rrf
            fused[topic_id]["keyword_score"] = item.get("keyword_score", 0)
            fused[topic_id]["keyword_rank"] = item.get("keyword_rank")
        
        return fused
    
    async def benchmark_search_methods(
        self,
        query: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Compare vector-only, keyword-only, and hybrid search.
        
        Useful for evaluating RRF effectiveness.
        """
        import time
        
        # Vector-only
        start = time.time()
        vector_results = await self._vector_search(query, limit, 72)
        vector_time = time.time() - start
        
        # Keyword-only
        start = time.time()
        keyword_results = await self._keyword_search(query, limit, 72)
        keyword_time = time.time() - start
        
        # Hybrid
        start = time.time()
        hybrid_results = await self.hybrid_search(query, limit)
        hybrid_time = time.time() - start
        
        return {
            "query": query,
            "vector": {
                "count": len(vector_results),
                "time_ms": round(vector_time * 1000, 2),
                "top_3": [r["title"][:50] for r in vector_results[:3]]
            },
            "keyword": {
                "count": len(keyword_results),
                "time_ms": round(keyword_time * 1000, 2),
                "top_3": [r["title"][:50] for r in keyword_results[:3]]
            },
            "hybrid": {
                "count": len(hybrid_results),
                "time_ms": round(hybrid_time * 1000, 2),
                "top_3": [r["title"][:50] for r in hybrid_results[:3]]
            }
        }


# =========================================================================
# Singleton
# =========================================================================

_client: Optional[PerceptionQdrantClient] = None


def get_qdrant_client() -> PerceptionQdrantClient:
    """Get or create the Qdrant client singleton."""
    global _client
    if _client is None:
        _client = PerceptionQdrantClient()
    return _client
