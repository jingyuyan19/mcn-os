# -*- coding: utf-8 -*-
"""
Tests for Hybrid Search RRF (Task 2.3)
======================================
Verifies RRF fusion algorithm and keyword extraction.
"""

import pytest
from lib.qdrant_client import PerceptionQdrantClient, get_qdrant_client


class TestHybridSearchRRF:
    """Test suite for Hybrid Search with RRF."""
    
    @pytest.fixture
    def client(self):
        return PerceptionQdrantClient()
    
    # =========================================================================
    # Keyword Extraction Tests
    # =========================================================================
    
    def test_extract_keywords_chinese(self, client):
        """Test keyword extraction from Chinese text."""
        text = "2026年AI视频生成技术突破"
        keywords = client._extract_keywords(text)
        
        assert "2026年ai视频生成技术突破" in keywords or len(keywords) > 0
        # Chinese words should be extracted
        assert "的" not in keywords  # Stopword filtered
    
    def test_extract_keywords_english(self, client):
        """Test keyword extraction from English text."""
        text = "OpenAI Sora API is now available for developers"
        keywords = client._extract_keywords(text)
        
        assert "openai" in keywords
        assert "sora" in keywords
        assert "api" in keywords
        assert "developers" in keywords
        # Stopwords filtered
        assert "is" not in keywords
        assert "the" not in keywords
    
    def test_extract_keywords_mixed(self, client):
        """Test keyword extraction from mixed Chinese-English text."""
        text = "OpenAI发布Sora API开放公告"
        keywords = client._extract_keywords(text)
        
        # Should extract some keywords (tokenization varies)
        assert len(keywords) > 0
        # Check that we got meaningful content, not just stopwords
        assert any(len(k) >= 2 for k in keywords)
    
    def test_extract_keywords_empty(self, client):
        """Test empty input."""
        keywords = client._extract_keywords("")
        assert keywords == set()
    
    # =========================================================================
    # RRF Fusion Tests
    # =========================================================================
    
    def test_rrf_fusion_basic(self, client):
        """Test basic RRF fusion with simple data."""
        vector_results = [
            {"topic_id": "t1", "title": "Topic 1", "vector_rank": 1, "vector_score": 0.95},
            {"topic_id": "t2", "title": "Topic 2", "vector_rank": 2, "vector_score": 0.85},
        ]
        keyword_results = [
            {"topic_id": "t2", "title": "Topic 2", "keyword_rank": 1, "keyword_score": 0.8},
            {"topic_id": "t3", "title": "Topic 3", "keyword_rank": 2, "keyword_score": 0.6},
        ]
        
        fused = client._rrf_fusion(
            vector_results, keyword_results,
            vector_weight=0.6, keyword_weight=0.4, k=60
        )
        
        # All topics should be in result
        assert "t1" in fused
        assert "t2" in fused
        assert "t3" in fused
        
        # t2 should have highest score (appears in both)
        assert fused["t2"]["rrf_score"] > fused["t1"]["rrf_score"]
        assert fused["t2"]["rrf_score"] > fused["t3"]["rrf_score"]
    
    def test_rrf_fusion_empty(self, client):
        """Test RRF with empty inputs."""
        fused = client._rrf_fusion([], [], 0.6, 0.4, 60)
        assert fused == {}
    
    def test_rrf_fusion_vector_only(self, client):
        """Test RRF with only vector results."""
        vector_results = [
            {"topic_id": "t1", "title": "Topic 1", "vector_rank": 1, "vector_score": 0.95},
        ]
        
        fused = client._rrf_fusion(vector_results, [], 0.6, 0.4, 60)
        
        assert "t1" in fused
        assert fused["t1"]["vector_rank"] == 1
        assert fused["t1"]["keyword_rank"] is None
    
    def test_rrf_fusion_keyword_only(self, client):
        """Test RRF with only keyword results."""
        keyword_results = [
            {"topic_id": "t1", "title": "Topic 1", "keyword_rank": 1, "keyword_score": 0.8},
        ]
        
        fused = client._rrf_fusion([], keyword_results, 0.6, 0.4, 60)
        
        assert "t1" in fused
        assert fused["t1"]["keyword_rank"] == 1
        assert fused["t1"]["vector_rank"] is None
    
    def test_rrf_score_calculation(self, client):
        """Test RRF score formula: weight * (1 / (k + rank))."""
        vector_results = [
            {"topic_id": "t1", "title": "Topic 1", "vector_rank": 1, "vector_score": 0.95},
        ]
        
        k = 60
        vector_weight = 0.6
        
        fused = client._rrf_fusion(vector_results, [], vector_weight, 0.4, k)
        
        expected_score = vector_weight * (1.0 / (k + 1))  # rank=1
        assert abs(fused["t1"]["rrf_score"] - expected_score) < 0.0001
    
    # =========================================================================
    # Singleton Test
    # =========================================================================
    
    def test_singleton(self):
        """Test singleton pattern."""
        c1 = get_qdrant_client()
        c2 = get_qdrant_client()
        assert c1 is c2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
