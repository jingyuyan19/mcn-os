# -*- coding: utf-8 -*-
"""
Intent Router: Adaptive RAG Query Classifier
=============================================
Classifies user queries/topics to route to the optimal research path.

Routes:
- internal_kb: Query artist knowledge base (OpenNotebook)
- external_web: Search web for current information (MiroThinker)
- direct_gen: No retrieval needed, direct LLM generation
- hybrid: Combine KB + Web search

Architecture Reference: PERCEPTION_ARCHITECTURE.md §5
"""

import os
import re
import json
import logging
from typing import Dict, Any, List, Literal, Optional
from dataclasses import dataclass

import httpx

logger = logging.getLogger("IntentRouter")


# =========================================================================
# Intent Types
# =========================================================================

IntentType = Literal["internal_kb", "external_web", "direct_gen", "hybrid"]


@dataclass
class RoutingDecision:
    """Result of intent classification."""
    intent: IntentType
    confidence: float
    reasoning: str
    suggested_agent: str
    fallback_intent: Optional[IntentType] = None


# =========================================================================
# Routing Rules (Heuristic Layer)
# =========================================================================

# Keywords that suggest internal KB search
KB_KEYWORDS = [
    "我们", "之前", "上次", "历史", "过去", "这个艺人", "这位艺人",
    "以前", "曾经", "记录", "数据", "统计", "表现", "我的",
    "our", "previous", "history", "before", "artist", "past", "data"
]

# Keywords that suggest web search
WEB_KEYWORDS = [
    "最新", "今天", "现在", "刚刚", "新闻", "热点", "趋势",
    "latest", "today", "now", "news", "trending", "current", "recent",
    "2026", "2025", "昨天", "本周", "这周"
]

# Keywords that suggest direct generation (no retrieval)
DIRECT_GEN_KEYWORDS = [
    "创意", "想法", "建议", "灵感", "点子", "标题", "起个",
    "ideas", "suggest", "creative", "brainstorm", "title", "generate"
]


class IntentRouter:
    """
    Adaptive RAG Router for query intent classification.
    
    Uses a two-stage approach:
    1. Fast heuristic check (keywords, patterns)
    2. LLM classifier for ambiguous cases (Gemini Flash)
    
    Usage:
        router = get_intent_router()
        decision = await router.classify("What's the latest AI news?")
        # decision.intent = "external_web"
    """
    
    def __init__(self):
        self.antigravity_url = os.getenv(
            "ANTIGRAVITY_BASE_URL", 
            "http://127.0.0.1:8045/v1"
        )
        self.model = "gemini-2.0-flash"  # Fast model for classification
        logger.info("IntentRouter initialized")
    
    async def classify(
        self,
        query: str,
        context: Optional[Dict] = None
    ) -> RoutingDecision:
        """
        Classify query intent for optimal routing.
        
        Args:
            query: User query or topic title
            context: Optional context (artist_id, source_type, etc.)
            
        Returns:
            RoutingDecision with intent, confidence, and reasoning
        """
        context = context or {}
        
        # Stage 1: Fast heuristic classification
        heuristic_result = self._heuristic_classify(query, context)
        
        if heuristic_result and heuristic_result.confidence >= 0.8:
            logger.info(f"Heuristic classification: {heuristic_result.intent} ({heuristic_result.confidence:.2f})")
            return heuristic_result
        
        # Stage 2: LLM classification for ambiguous cases
        llm_result = await self._llm_classify(query, context)
        
        # Combine results if both available
        if heuristic_result and llm_result:
            return self._combine_results(heuristic_result, llm_result)
        
        return llm_result or heuristic_result or RoutingDecision(
            intent="hybrid",
            confidence=0.5,
            reasoning="Fallback to hybrid when classification uncertain",
            suggested_agent="mirothinker"
        )
    
    def _heuristic_classify(
        self,
        query: str,
        context: Dict
    ) -> Optional[RoutingDecision]:
        """
        Fast keyword-based classification.
        
        Returns high-confidence result for clear cases,
        or low-confidence hint for ambiguous cases.
        """
        query_lower = query.lower()
        
        # Count keyword matches
        kb_score = sum(1 for kw in KB_KEYWORDS if kw in query_lower)
        web_score = sum(1 for kw in WEB_KEYWORDS if kw in query_lower)
        gen_score = sum(1 for kw in DIRECT_GEN_KEYWORDS if kw in query_lower)
        
        # Context overrides
        source_type = context.get("source_type", "")
        if source_type == "knowledge_base":
            kb_score += 3
        elif source_type == "rss_feed":
            web_score += 3
        
        # Check for artist reference
        if context.get("artist_id") or context.get("notebook_id"):
            kb_score += 2
        
        # Determine winner
        max_score = max(kb_score, web_score, gen_score)
        
        if max_score == 0:
            return None  # No clear signal, need LLM
        
        total = kb_score + web_score + gen_score + 0.1
        
        if kb_score == max_score:
            confidence = min(kb_score / total + 0.3, 0.95)
            return RoutingDecision(
                intent="internal_kb",
                confidence=confidence,
                reasoning=f"Keywords suggest internal data lookup (score: {kb_score})",
                suggested_agent="open_notebook"
            )
        
        elif web_score == max_score:
            confidence = min(web_score / total + 0.3, 0.95)
            return RoutingDecision(
                intent="external_web",
                confidence=confidence,
                reasoning=f"Keywords suggest current events lookup (score: {web_score})",
                suggested_agent="mirothinker"
            )
        
        else:  # gen_score
            confidence = min(gen_score / total + 0.3, 0.95)
            return RoutingDecision(
                intent="direct_gen",
                confidence=confidence,
                reasoning=f"Keywords suggest creative generation (score: {gen_score})",
                suggested_agent="gemini"
            )
    
    async def _llm_classify(
        self,
        query: str,
        context: Dict
    ) -> Optional[RoutingDecision]:
        """
        LLM-based classification using Gemini Flash.
        
        Used when heuristics are inconclusive.
        """
        system_prompt = """You are a query intent classifier for an AI content creation system.

Classify the query into ONE of these categories:

1. **internal_kb** - Query needs data from our internal knowledge base
   - Artist-specific history, past content, performance data
   - Curated research documents, course materials
   - Example: "What topics did we cover last week?"

2. **external_web** - Query needs current web information
   - Breaking news, trending topics, recent events
   - General knowledge that changes frequently
   - Example: "What's the latest on AI regulation?"

3. **direct_gen** - Query needs creative generation, no retrieval
   - Brainstorming, ideation, title suggestions
   - Creative writing, script ideas
   - Example: "Give me 5 catchy video titles about cooking"

4. **hybrid** - Query needs BOTH internal KB AND external web
   - Comparing our past work to current trends
   - Enriching KB knowledge with fresh data
   - Example: "How does our coverage compare to new developments?"

Respond with JSON only:
{"intent": "...", "confidence": 0.0-1.0, "reasoning": "..."}"""

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.antigravity_url}/chat/completions",
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"Classify this query: {query}"}
                        ],
                        "temperature": 0.1,  # Low temp for classification
                        "max_tokens": 150
                    }
                )
                result = response.json()
            
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "{}")
            
            # Parse JSON from response
            json_match = re.search(r'\{[^}]+\}', content)
            if json_match:
                parsed = json.loads(json_match.group())
                
                intent = parsed.get("intent", "hybrid")
                if intent not in ["internal_kb", "external_web", "direct_gen", "hybrid"]:
                    intent = "hybrid"
                
                return RoutingDecision(
                    intent=intent,
                    confidence=float(parsed.get("confidence", 0.7)),
                    reasoning=parsed.get("reasoning", "LLM classification"),
                    suggested_agent=self._intent_to_agent(intent)
                )
                
        except Exception as e:
            logger.warning(f"LLM classification failed: {e}")
            return None
        
        return None
    
    def _combine_results(
        self,
        heuristic: RoutingDecision,
        llm: RoutingDecision
    ) -> RoutingDecision:
        """Combine heuristic and LLM results for final decision."""
        
        # If they agree, boost confidence
        if heuristic.intent == llm.intent:
            return RoutingDecision(
                intent=llm.intent,
                confidence=min((heuristic.confidence + llm.confidence) / 2 + 0.1, 0.99),
                reasoning=f"Heuristic + LLM agree: {llm.reasoning}",
                suggested_agent=llm.suggested_agent
            )
        
        # If they disagree, prefer LLM but note the conflict
        if llm.confidence > heuristic.confidence:
            return RoutingDecision(
                intent=llm.intent,
                confidence=llm.confidence * 0.9,  # Slight penalty for disagreement
                reasoning=f"LLM override: {llm.reasoning} (heuristic suggested {heuristic.intent})",
                suggested_agent=llm.suggested_agent,
                fallback_intent=heuristic.intent
            )
        else:
            return RoutingDecision(
                intent=heuristic.intent,
                confidence=heuristic.confidence * 0.9,
                reasoning=f"Heuristic preferred: {heuristic.reasoning} (LLM suggested {llm.intent})",
                suggested_agent=heuristic.suggested_agent,
                fallback_intent=llm.intent
            )
    
    def _intent_to_agent(self, intent: IntentType) -> str:
        """Map intent to suggested research agent."""
        mapping = {
            "internal_kb": "open_notebook",
            "external_web": "mirothinker",
            "direct_gen": "gemini",
            "hybrid": "mirothinker"  # MiroThinker handles hybrid well
        }
        return mapping.get(intent, "mirothinker")
    
    # =========================================================================
    # Batch Classification
    # =========================================================================
    
    async def classify_batch(
        self,
        queries: List[str],
        context: Optional[Dict] = None
    ) -> List[RoutingDecision]:
        """
        Classify multiple queries in parallel.
        
        Useful for processing multiple topics at once.
        """
        import asyncio
        
        tasks = [self.classify(q, context) for q in queries]
        return await asyncio.gather(*tasks)
    
    # =========================================================================
    # Route Execution
    # =========================================================================
    
    async def route_and_execute(
        self,
        query: str,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Classify and execute the appropriate research path.
        
        This is a convenience method that combines classification
        with agent execution.
        
        Args:
            query: User query
            context: Optional context dict
            
        Returns:
            {
                "decision": RoutingDecision,
                "result": agent_output,
                "agent_used": "open_notebook" | "mirothinker" | "gemini"
            }
        """
        decision = await self.classify(query, context)
        
        logger.info(f"Routing '{query[:50]}...' to {decision.intent} ({decision.suggested_agent})")
        
        result = None
        
        if decision.intent == "internal_kb":
            result = await self._execute_kb_search(query, context)
            
        elif decision.intent == "external_web":
            result = await self._execute_web_search(query, context)
            
        elif decision.intent == "direct_gen":
            result = await self._execute_direct_gen(query, context)
            
        else:  # hybrid
            result = await self._execute_hybrid(query, context)
        
        return {
            "decision": decision,
            "result": result,
            "agent_used": decision.suggested_agent
        }
    
    async def _execute_kb_search(self, query: str, context: Dict) -> Dict:
        """Execute internal KB search via OpenNotebook."""
        from lib.open_notebook_client import get_open_notebook_client
        
        client = get_open_notebook_client()
        notebook_id = context.get("notebook_id")
        
        if not notebook_id:
            # Try to get from artist
            artist_id = context.get("artist_id")
            if artist_id:
                from lib.sanity_client import get_sanity_client
                sanity = get_sanity_client()
                artist = sanity.query(
                    '*[_type == "artist" && _id == $id][0]',
                    {"id": artist_id}
                )
                notebook_id = artist.get("knowledgeBase", {}).get("notebookId")
        
        if not notebook_id:
            return {"error": "No notebook_id available", "fallback": "external_web"}
        
        return await client.ask(notebook_id, query)
    
    async def _execute_web_search(self, query: str, context: Dict) -> Dict:
        """Execute web search via MiroThinker."""
        from lib.mirothinker_client import get_mirothinker_client
        
        client = get_mirothinker_client()
        return await client.deep_research(
            query=query,
            max_turns=20,
            min_scraped_pages=2
        )
    
    async def _execute_direct_gen(self, query: str, context: Dict) -> Dict:
        """Execute direct generation via Gemini (no retrieval)."""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.antigravity_url}/chat/completions",
                    json={
                        "model": "gemini-2.0-flash",
                        "messages": [
                            {"role": "user", "content": query}
                        ],
                        "temperature": 0.8
                    }
                )
                result = response.json()
            
            return {
                "response": result.get("choices", [{}])[0].get("message", {}).get("content", ""),
                "sources": []
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def _execute_hybrid(self, query: str, context: Dict) -> Dict:
        """Execute hybrid search (KB + Web)."""
        import asyncio
        
        # Run both in parallel
        kb_task = self._execute_kb_search(query, context)
        web_task = self._execute_web_search(query, context)
        
        kb_result, web_result = await asyncio.gather(
            kb_task, web_task,
            return_exceptions=True
        )
        
        return {
            "kb_result": kb_result if not isinstance(kb_result, Exception) else {"error": str(kb_result)},
            "web_result": web_result if not isinstance(web_result, Exception) else {"error": str(web_result)},
            "combined": True
        }


# =========================================================================
# Singleton
# =========================================================================

_router: Optional[IntentRouter] = None


def get_intent_router() -> IntentRouter:
    """Get or create the IntentRouter singleton."""
    global _router
    if _router is None:
        _router = IntentRouter()
    return _router
