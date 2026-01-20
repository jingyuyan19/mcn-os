# -*- coding: utf-8 -*-
"""
Tests for Intent Router
=======================
Verifies query classification and routing logic.
"""

import pytest
from lib.intent_router import (
    IntentRouter,
    RoutingDecision,
    get_intent_router,
    KB_KEYWORDS,
    WEB_KEYWORDS,
    DIRECT_GEN_KEYWORDS
)


class TestIntentRouter:
    """Test suite for Intent Router."""
    
    @pytest.fixture
    def router(self):
        return IntentRouter()
    
    # =========================================================================
    # Heuristic Classification Tests
    # =========================================================================
    
    def test_heuristic_kb_keywords(self, router):
        """Test internal KB detection via keywords."""
        result = router._heuristic_classify(
            "我们之前发布过什么内容？",
            {}
        )
        assert result is not None
        assert result.intent == "internal_kb"
        assert result.confidence >= 0.5
    
    def test_heuristic_web_keywords(self, router):
        """Test web search detection via keywords."""
        result = router._heuristic_classify(
            "最新的AI新闻是什么？今天有什么热点？",
            {}
        )
        assert result is not None
        assert result.intent == "external_web"
        assert result.confidence >= 0.5
    
    def test_heuristic_direct_gen_keywords(self, router):
        """Test direct generation detection via keywords."""
        result = router._heuristic_classify(
            "帮我想几个创意标题",
            {}
        )
        assert result is not None
        assert result.intent == "direct_gen"
        assert result.confidence >= 0.5
    
    def test_heuristic_context_override(self, router):
        """Test context can boost KB score."""
        result = router._heuristic_classify(
            "这个话题怎么样？",  # Ambiguous query
            {"source_type": "knowledge_base", "artist_id": "artist_123"}
        )
        assert result is not None
        assert result.intent == "internal_kb"  # Context boosted KB
    
    def test_heuristic_no_keywords(self, router):
        """Test fallback when no keywords match."""
        result = router._heuristic_classify(
            "你好",  # No keywords
            {}
        )
        assert result is None  # Should return None, triggering LLM
    
    # =========================================================================
    # Agent Mapping Tests
    # =========================================================================
    
    def test_intent_to_agent_mapping(self, router):
        """Test intent to agent mapping."""
        assert router._intent_to_agent("internal_kb") == "open_notebook"
        assert router._intent_to_agent("external_web") == "mirothinker"
        assert router._intent_to_agent("direct_gen") == "gemini"
        assert router._intent_to_agent("hybrid") == "mirothinker"
    
    # =========================================================================
    # Combine Results Tests
    # =========================================================================
    
    def test_combine_agreement(self, router):
        """Test combining when heuristic and LLM agree."""
        heuristic = RoutingDecision(
            intent="external_web",
            confidence=0.7,
            reasoning="Keywords",
            suggested_agent="mirothinker"
        )
        llm = RoutingDecision(
            intent="external_web",
            confidence=0.8,
            reasoning="LLM agrees",
            suggested_agent="mirothinker"
        )
        
        result = router._combine_results(heuristic, llm)
        
        assert result.intent == "external_web"
        assert result.confidence > max(heuristic.confidence, llm.confidence)  # Boosted
    
    def test_combine_disagreement_llm_wins(self, router):
        """Test combining when LLM has higher confidence."""
        heuristic = RoutingDecision(
            intent="internal_kb",
            confidence=0.5,
            reasoning="Keywords",
            suggested_agent="open_notebook"
        )
        llm = RoutingDecision(
            intent="external_web",
            confidence=0.9,
            reasoning="LLM override",
            suggested_agent="mirothinker"
        )
        
        result = router._combine_results(heuristic, llm)
        
        assert result.intent == "external_web"  # LLM wins
        assert result.fallback_intent == "internal_kb"  # But heuristic noted
    
    # =========================================================================
    # Full Classification Tests (Async)
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_classify_high_confidence_heuristic(self, router):
        """Test classification with clear heuristic match."""
        # High-confidence heuristic should skip LLM
        result = await router.classify(
            "我们上次发布的历史数据是什么？过去的记录呢？",
            {}
        )
        
        assert result.intent == "internal_kb"
        assert result.confidence >= 0.7
    
    @pytest.mark.asyncio
    async def test_classify_with_context(self, router):
        """Test classification uses context properly."""
        result = await router.classify(
            "这个话题的表现如何？",
            {"source_type": "knowledge_base", "notebook_id": "nb_123"}
        )
        
        # Context should push towards internal_kb
        assert result.suggested_agent in ["open_notebook", "mirothinker"]
    
    # =========================================================================
    # Singleton Test
    # =========================================================================
    
    def test_singleton(self):
        """Test singleton pattern."""
        r1 = get_intent_router()
        r2 = get_intent_router()
        assert r1 is r2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
