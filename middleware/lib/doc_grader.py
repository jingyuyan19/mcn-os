# -*- coding: utf-8 -*-
"""
Document Grader: Corrective RAG (CRAG) Implementation
======================================================
Grades retrieved documents for relevance before passing to LLM.
Irrelevant documents cause hallucinations - CRAG filters them out.

Grades:
- relevant (>0.7): Pass to generator
- ambiguous (0.4-0.7): Rewrite query, re-search
- irrelevant (<0.4): Discard, try web fallback

Architecture Reference: PERCEPTION_ARCHITECTURE.md §6
"""

import os
import re
import json
import logging
from typing import Dict, Any, List, Literal, Optional, Tuple
from dataclasses import dataclass

import httpx

logger = logging.getLogger("DocumentGrader")


# =========================================================================
# Grade Types
# =========================================================================

GradeLevel = Literal["relevant", "ambiguous", "irrelevant"]


@dataclass
class GradedDocument:
    """A document with relevance grade."""
    document: Dict[str, Any]
    score: float
    grade: GradeLevel
    reasoning: str
    
    @property
    def is_usable(self) -> bool:
        """Check if document should be used for generation."""
        return self.grade in ["relevant", "ambiguous"]


@dataclass
class GradingResult:
    """Result of grading a batch of documents."""
    graded_docs: List[GradedDocument]
    relevant_count: int
    ambiguous_count: int
    irrelevant_count: int
    needs_rewrite: bool
    suggested_action: Literal["proceed", "rewrite", "web_fallback"]


# =========================================================================
# Document Grader
# =========================================================================

class DocumentGrader:
    """
    CRAG Document Grader - filters irrelevant docs before LLM generation.
    
    Usage:
        grader = get_doc_grader()
        result = await grader.grade_documents(query, documents)
        
        if result.needs_rewrite:
            new_query = await grader.rewrite_query(query, result)
    """
    
    # Score thresholds
    RELEVANT_THRESHOLD = 0.7
    AMBIGUOUS_THRESHOLD = 0.4
    
    def __init__(self):
        self.antigravity_url = os.getenv(
            "ANTIGRAVITY_BASE_URL",
            "http://127.0.0.1:8045/v1"
        )
        self.model = "gemini-2.0-flash"
        logger.info("DocumentGrader initialized")
    
    async def grade_documents(
        self,
        query: str,
        documents: List[Dict[str, Any]]
    ) -> GradingResult:
        """
        Grade each document for relevance to the query.
        
        Args:
            query: User query or topic
            documents: List of retrieved documents
            
        Returns:
            GradingResult with graded docs and suggested action
        """
        if not documents:
            return GradingResult(
                graded_docs=[],
                relevant_count=0,
                ambiguous_count=0,
                irrelevant_count=0,
                needs_rewrite=False,
                suggested_action="web_fallback"
            )
        
        graded = []
        
        for doc in documents:
            score, reasoning = await self._grade_single(query, doc)
            grade = self._score_to_grade(score)
            
            graded.append(GradedDocument(
                document=doc,
                score=score,
                grade=grade,
                reasoning=reasoning
            ))
        
        # Count grades
        relevant = sum(1 for g in graded if g.grade == "relevant")
        ambiguous = sum(1 for g in graded if g.grade == "ambiguous")
        irrelevant = sum(1 for g in graded if g.grade == "irrelevant")
        
        # Determine action
        if relevant >= 1:
            action = "proceed"
            needs_rewrite = False
        elif ambiguous >= 1:
            action = "rewrite"
            needs_rewrite = True
        else:
            action = "web_fallback"
            needs_rewrite = False
        
        logger.info(f"Graded {len(documents)} docs: {relevant} relevant, {ambiguous} ambiguous, {irrelevant} irrelevant → {action}")
        
        return GradingResult(
            graded_docs=graded,
            relevant_count=relevant,
            ambiguous_count=ambiguous,
            irrelevant_count=irrelevant,
            needs_rewrite=needs_rewrite,
            suggested_action=action
        )
    
    async def _grade_single(
        self,
        query: str,
        document: Dict[str, Any]
    ) -> Tuple[float, str]:
        """
        Grade a single document for relevance.
        
        Returns (score, reasoning) tuple.
        """
        # Extract document content
        content = self._extract_content(document)
        
        if not content:
            return 0.0, "Empty document content"
        
        # Fast heuristic check
        heuristic_score = self._heuristic_grade(query, content)
        if heuristic_score is not None:
            return heuristic_score
        
        # LLM grading for ambiguous cases
        return await self._llm_grade(query, content)
    
    def _extract_content(self, document: Dict) -> str:
        """Extract readable content from document."""
        content_fields = ["content", "text", "excerpt", "snippet", "body", "response"]
        
        for field in content_fields:
            if field in document and document[field]:
                return str(document[field])[:2000]
        
        # Fallback: stringify the whole thing
        return str(document)[:2000]
    
    def _heuristic_grade(
        self,
        query: str,
        content: str
    ) -> Optional[Tuple[float, str]]:
        """
        Fast heuristic grading for obvious cases.
        
        Returns (score, reasoning) or None if LLM needed.
        """
        query_lower = query.lower()
        content_lower = content.lower()
        
        # Extract keywords from query
        query_words = set(re.findall(r'\b\w{3,}\b', query_lower))
        
        if not query_words:
            return None
        
        # Count keyword matches
        matches = sum(1 for word in query_words if word in content_lower)
        match_ratio = matches / len(query_words)
        
        # High match = clearly relevant
        if match_ratio >= 0.8:
            return (0.9, f"High keyword match ({matches}/{len(query_words)} words)")
        
        # No match = clearly irrelevant
        if match_ratio == 0:
            return (0.1, "No keyword overlap with query")
        
        # Ambiguous cases need LLM
        return None
    
    async def _llm_grade(
        self,
        query: str,
        content: str
    ) -> Tuple[float, str]:
        """LLM-based relevance grading."""
        
        prompt = f"""Rate how relevant this document is to the query.

QUERY: {query}

DOCUMENT (excerpt):
{content[:1500]}

Respond with JSON only:
{{"score": 0.0-1.0, "reasoning": "brief explanation"}}

Score guide:
- 0.8-1.0: Directly answers the query
- 0.5-0.7: Partially relevant, some useful info
- 0.2-0.4: Tangentially related
- 0.0-0.2: Completely off-topic"""

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    f"{self.antigravity_url}/chat/completions",
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.1,
                        "max_tokens": 100
                    }
                )
                result = response.json()
            
            text = result.get("choices", [{}])[0].get("message", {}).get("content", "{}")
            
            # Parse JSON
            json_match = re.search(r'\{[^}]+\}', text)
            if json_match:
                parsed = json.loads(json_match.group())
                score = float(parsed.get("score", 0.5))
                reasoning = parsed.get("reasoning", "LLM grading")
                return (max(0.0, min(1.0, score)), reasoning)
                
        except Exception as e:
            logger.warning(f"LLM grading failed: {e}")
        
        # Fallback to medium score
        return (0.5, "Grading fallback (LLM unavailable)")
    
    def _score_to_grade(self, score: float) -> GradeLevel:
        """Convert numeric score to grade level."""
        if score >= self.RELEVANT_THRESHOLD:
            return "relevant"
        elif score >= self.AMBIGUOUS_THRESHOLD:
            return "ambiguous"
        else:
            return "irrelevant"
    
    # =========================================================================
    # Query Rewriter
    # =========================================================================
    
    async def rewrite_query(
        self,
        original_query: str,
        grading_result: GradingResult
    ) -> str:
        """
        Rewrite query to improve retrieval.
        
        Called when documents are ambiguous - reformulates the query
        to be more specific or approach from different angle.
        """
        # Collect reasoning from ambiguous docs
        ambiguous_reasons = [
            g.reasoning for g in grading_result.graded_docs 
            if g.grade == "ambiguous"
        ]
        
        prompt = f"""The following query retrieved documents that were only partially relevant.
Rewrite the query to be MORE SPECIFIC and retrieve better documents.

ORIGINAL QUERY: {original_query}

WHY DOCUMENTS WERE AMBIGUOUS:
{chr(10).join(['- ' + r for r in ambiguous_reasons[:3]])}

Write a better query (just the query, no explanation):"""

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"{self.antigravity_url}/chat/completions",
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.3,
                        "max_tokens": 100
                    }
                )
                result = response.json()
            
            new_query = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            new_query = new_query.strip().strip('"\'')
            
            if new_query and len(new_query) > 5:
                logger.info(f"Query rewritten: '{original_query[:30]}...' → '{new_query[:30]}...'")
                return new_query
                
        except Exception as e:
            logger.warning(f"Query rewrite failed: {e}")
        
        return original_query  # Fallback to original
    
    # =========================================================================
    # Filter for Generation
    # =========================================================================
    
    def filter_for_generation(
        self,
        grading_result: GradingResult
    ) -> List[Dict[str, Any]]:
        """
        Get only usable documents for LLM generation.
        
        Filters out irrelevant documents to reduce hallucinations.
        """
        return [
            g.document for g in grading_result.graded_docs
            if g.is_usable
        ]
    
    def get_top_documents(
        self,
        grading_result: GradingResult,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get top N documents sorted by relevance score."""
        sorted_docs = sorted(
            grading_result.graded_docs,
            key=lambda g: g.score,
            reverse=True
        )
        return [g.document for g in sorted_docs[:limit] if g.is_usable]


# =========================================================================
# Singleton
# =========================================================================

_grader: Optional[DocumentGrader] = None


def get_doc_grader() -> DocumentGrader:
    """Get or create the DocumentGrader singleton."""
    global _grader
    if _grader is None:
        _grader = DocumentGrader()
    return _grader
