# -*- coding: utf-8 -*-
"""
IR Normalizer: Universal Context Schema (UCS) Transformer
==========================================================
Normalizes outputs from multiple research agents into a unified format
for consistent downstream processing by Gemini.

Supports:
- BettaFish IR (block-based: kpiGrid, engineQuote, paragraph)
- MiroThinker reports (detailed_report, short_answer, references)
- OpenNotebook RAG (answer, citations, sources_used)

Usage:
    from lib.ir_normalizer import IRNormalizer
    
    normalizer = IRNormalizer()
    ucs = normalizer.normalize_bettafish_ir(bettafish_output)
    ucs = normalizer.normalize_mirothinker_report(mirothinker_output)
    ucs = normalizer.normalize_opennotebook_rag(opennotebook_output)

Architecture Reference: PERCEPTION_ARCHITECTURE.md §4
"""

import logging
import re
from typing import TypedDict, List, Optional, Dict, Any, Literal
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("IRNormalizer")


# =========================================================================
# Universal Context Schema (UCS) Type Definition
# =========================================================================

class UCSSentiment(TypedDict):
    """Public sentiment analysis."""
    emotion: Literal["positive", "negative", "neutral", "controversial", "mixed"]
    key_quotes: List[str]
    controversy_ratio: float


class UCSReference(TypedDict):
    """Source reference with credibility tier."""
    title: str
    url: str
    credibility: Literal["tier1", "tier2", "tier3", "unknown"]
    snippet: Optional[str]


class UCSAnalysis(TypedDict):
    """Analytical content derived from research."""
    implications: str
    hook_angles: List[str]
    controversy_points: List[str]


class UCSMeta(TypedDict):
    """Metadata about the source and research process."""
    source_type: Literal["social", "rss", "knowledge_base"]
    research_agent: Literal["bettafish", "mirothinker", "open_notebook"]
    primary_url: Optional[str]
    topic_id: Optional[str]
    platform: Optional[str]
    freshness_hours: Optional[int]
    research_turns: Optional[int]
    sources_scraped: Optional[int]


class UniversalContextSchema(TypedDict):
    """
    Universal Context Schema (UCS) - The unified IR format.
    
    All research outputs are normalized to this format before
    being passed to Gemini for script generation.
    """
    meta: UCSMeta
    core_event: str  # One-sentence 'what happened'
    public_sentiment: UCSSentiment
    visual_cues: List[str]  # Trending hashtags, meme formats, etc.
    analysis: UCSAnalysis
    references: List[UCSReference]
    raw_content: Optional[str]  # Preserved detailed report for deep dives


# =========================================================================
# IR Normalizer Implementation
# =========================================================================

class IRNormalizer:
    """
    Transforms outputs from multiple research agents into UCS format.
    
    This is the critical integration layer that enables consistent
    prompting regardless of which research agent was used.
    """
    
    # Credibility tier mappings
    TIER1_DOMAINS = [
        "reuters.com", "apnews.com", "bbc.com", "nytimes.com",
        "xinhuanet.com", "people.com.cn", "cctv.com",
        "36kr.com", "jiqizhixin.com"  # Tech tier1 in China
    ]
    
    TIER2_DOMAINS = [
        "techcrunch.com", "theverge.com", "wired.com",
        "36kr.com", "sspai.com", "zhihu.com",
        "weibo.com", "xiaohongshu.com"
    ]
    
    def normalize_bettafish_ir(
        self,
        ir_document: Dict[str, Any],
        source_type: str = "social"
    ) -> UniversalContextSchema:
        """
        Normalize BettaFish IR block-based format to UCS.
        
        BettaFish IR uses:
        - kpiGrid: Engagement metrics (likes, comments, velocity)
        - engineQuote: Attributed content from insight agents
        - paragraph: Text content with inline marks
        - callout: Featured content (vernacular cloud, etc.)
        
        Args:
            ir_document: BettaFish IR from get_topic_ir()
            source_type: "social" or "rss"
            
        Returns:
            UniversalContextSchema dict
        """
        blocks = ir_document.get("blocks", [])
        
        # Extract from blocks
        engagement = self._extract_engagement_from_blocks(blocks)
        quotes = self._extract_quotes_from_blocks(blocks)
        vernacular = self._extract_vernacular_from_blocks(blocks)
        sentiment_text = self._extract_sentiment_from_blocks(blocks)
        
        # Parse sentiment
        emotion = self._classify_emotion(sentiment_text, engagement)
        controversy = engagement.get("controversy_ratio", 0)
        
        # Build UCS
        return UniversalContextSchema(
            meta=UCSMeta(
                source_type=source_type,
                research_agent="bettafish",
                primary_url=ir_document.get("url"),
                topic_id=ir_document.get("document_id"),
                platform=ir_document.get("platform"),
                freshness_hours=engagement.get("freshness_hours"),
                research_turns=None,
                sources_scraped=None
            ),
            core_event=ir_document.get("title", "Unknown topic"),
            public_sentiment=UCSSentiment(
                emotion=emotion,
                key_quotes=quotes[:5],
                controversy_ratio=controversy
            ),
            visual_cues=vernacular[:10],
            analysis=UCSAnalysis(
                implications=self._generate_implications(ir_document),
                hook_angles=self._extract_hook_angles(ir_document, quotes),
                controversy_points=self._extract_controversy_points(blocks)
            ),
            references=self._extract_references_from_ir(ir_document),
            raw_content=None  # BettaFish IR is structured, no raw content
        )
    
    def normalize_mirothinker_report(
        self,
        report: Dict[str, Any],
        source_type: str = "rss"
    ) -> UniversalContextSchema:
        """
        Normalize MiroThinker deep research report to UCS.
        
        MiroThinker output:
        - short_answer: Executive summary
        - detailed_report: Full markdown report with sections
        - references: List of {id, title, url, snippet}
        - turns_used: Research depth indicator
        - sources_scraped: Number of pages analyzed
        
        Args:
            report: MiroThinker output from deep_research()
            source_type: "rss" or "knowledge_base"
            
        Returns:
            UniversalContextSchema dict
        """
        detailed = report.get("detailed_report", "")
        short_answer = report.get("short_answer", "")
        refs = report.get("references", [])
        
        # Extract structured content from markdown
        findings = self._extract_findings_from_markdown(detailed)
        conflicts = self._extract_conflicts_from_markdown(detailed)
        
        # Infer emotion from content tone
        emotion = self._infer_emotion_from_text(short_answer + detailed[:500])
        
        return UniversalContextSchema(
            meta=UCSMeta(
                source_type=source_type,
                research_agent="mirothinker",
                primary_url=refs[0].get("url") if refs else None,
                topic_id=None,
                platform=None,
                freshness_hours=None,
                research_turns=report.get("turns_used"),
                sources_scraped=report.get("sources_scraped")
            ),
            core_event=short_answer[:500] if short_answer else "Research summary unavailable",
            public_sentiment=UCSSentiment(
                emotion=emotion,
                key_quotes=self._extract_quotes_from_markdown(detailed)[:5],
                controversy_ratio=0.3 if conflicts else 0.0
            ),
            visual_cues=[],  # MiroThinker doesn't track visual trends
            analysis=UCSAnalysis(
                implications=self._extract_section(detailed, "Conclusion"),
                hook_angles=findings[:3],
                controversy_points=conflicts[:3]
            ),
            references=[
                UCSReference(
                    title=r.get("title", "Unknown"),
                    url=r.get("url", ""),
                    credibility=self._classify_credibility(r.get("url", "")),
                    snippet=r.get("snippet")
                )
                for r in refs[:10]
            ],
            raw_content=detailed[:15000] if detailed else None
        )
    
    def normalize_opennotebook_rag(
        self,
        rag_result: Dict[str, Any],
        source_type: str = "knowledge_base"
    ) -> UniversalContextSchema:
        """
        Normalize OpenNotebook RAG answer to UCS.
        
        OpenNotebook output (from /chat or transform):
        - response: LLM answer text
        - sources: List of source documents used
        - citations: Inline citations extracted
        
        Args:
            rag_result: OpenNotebook chat/ask response
            source_type: Usually "knowledge_base"
            
        Returns:
            UniversalContextSchema dict
        """
        response = rag_result.get("response", "")
        sources = rag_result.get("sources", [])
        
        # Extract citations from response
        citations = self._extract_citations_from_text(response)
        
        return UniversalContextSchema(
            meta=UCSMeta(
                source_type=source_type,
                research_agent="open_notebook",
                primary_url=None,  # Local knowledge base
                topic_id=rag_result.get("notebook_id"),
                platform="open_notebook",
                freshness_hours=None,
                research_turns=None,
                sources_scraped=len(sources)
            ),
            core_event=response[:500] if response else "No response available",
            public_sentiment=UCSSentiment(
                emotion="neutral",  # KB content is typically objective
                key_quotes=citations[:5],
                controversy_ratio=0.0
            ),
            visual_cues=[],
            analysis=UCSAnalysis(
                implications="",
                hook_angles=self._extract_hook_angles_from_text(response),
                controversy_points=[]
            ),
            references=[
                UCSReference(
                    title=s.get("title", s.get("name", "Source")),
                    url=s.get("url", ""),
                    credibility="tier1",  # Curated KB is trusted
                    snippet=s.get("excerpt", s.get("content", ""))[:200]
                )
                for s in sources[:10]
            ],
            raw_content=response
        )
    
    def merge(
        self,
        primary: UniversalContextSchema,
        supplementary: UniversalContextSchema
    ) -> UniversalContextSchema:
        """
        Merge two UCS documents (e.g., KB + Web research).
        
        Primary's core_event and sentiment are preserved.
        References and analysis are combined.
        
        Args:
            primary: Main UCS (e.g., from Open Notebook)
            supplementary: Supporting UCS (e.g., from MiroThinker)
            
        Returns:
            Merged UniversalContextSchema
        """
        return UniversalContextSchema(
            meta=UCSMeta(
                source_type=primary["meta"]["source_type"],
                research_agent="merged",
                primary_url=primary["meta"].get("primary_url"),
                topic_id=primary["meta"].get("topic_id"),
                platform=primary["meta"].get("platform"),
                freshness_hours=primary["meta"].get("freshness_hours"),
                research_turns=supplementary["meta"].get("research_turns"),
                sources_scraped=(
                    (primary["meta"].get("sources_scraped") or 0) +
                    (supplementary["meta"].get("sources_scraped") or 0)
                )
            ),
            core_event=primary["core_event"],
            public_sentiment=primary["public_sentiment"],
            visual_cues=list(set(
                primary.get("visual_cues", []) + 
                supplementary.get("visual_cues", [])
            ))[:10],
            analysis=UCSAnalysis(
                implications=primary["analysis"]["implications"] or supplementary["analysis"]["implications"],
                hook_angles=list(set(
                    primary["analysis"]["hook_angles"] + 
                    supplementary["analysis"]["hook_angles"]
                ))[:5],
                controversy_points=list(set(
                    primary["analysis"]["controversy_points"] + 
                    supplementary["analysis"]["controversy_points"]
                ))[:5]
            ),
            references=primary["references"] + supplementary["references"],
            raw_content=primary.get("raw_content") or supplementary.get("raw_content")
        )
    
    # =========================================================================
    # Helper Methods: BettaFish Extraction
    # =========================================================================
    
    def _extract_engagement_from_blocks(self, blocks: List[Dict]) -> Dict:
        """Extract engagement metrics from kpiGrid blocks."""
        for block in blocks:
            if block.get("type") == "kpiGrid":
                items = block.get("items", [])
                result = {}
                for item in items:
                    label = item.get("label", "").lower()
                    value = item.get("value", "0")
                    
                    if label == "likes":
                        result["likes"] = self._parse_number(value)
                    elif label == "comments":
                        result["comments"] = self._parse_number(value)
                    elif label == "freshness":
                        result["freshness_hours"] = self._parse_hours(value)
                    elif label == "velocity":
                        result["velocity"] = value.lower()
                
                if result.get("likes") and result.get("comments"):
                    result["controversy_ratio"] = (
                        result["comments"] / max(result["likes"], 1)
                    )
                return result
        return {}
    
    def _extract_quotes_from_blocks(self, blocks: List[Dict]) -> List[str]:
        """Extract quotes from engineQuote blocks."""
        quotes = []
        for block in blocks:
            if block.get("type") == "engineQuote":
                for inner in block.get("blocks", []):
                    for inline in inner.get("inlines", []):
                        text = inline.get("text", "")
                        if text and text.startswith('"'):
                            quotes.append(text.strip('"'))
        return quotes
    
    def _extract_vernacular_from_blocks(self, blocks: List[Dict]) -> List[str]:
        """Extract trending vernacular from callout blocks."""
        for block in blocks:
            if block.get("type") == "callout" and "Vernacular" in block.get("title", ""):
                inner = block.get("blocks", [{}])[0]
                text = inner.get("inlines", [{}])[0].get("text", "")
                if text:
                    return [v.strip() for v in text.split("|")]
        return []
    
    def _extract_sentiment_from_blocks(self, blocks: List[Dict]) -> str:
        """Extract sentiment text from paragraph blocks."""
        for block in blocks:
            if block.get("type") == "paragraph":
                inlines = block.get("inlines", [])
                for inline in inlines:
                    if inline.get("marks") and "Sentiment" in str(inline.get("text", "")):
                        return inline.get("text", "")
        return ""
    
    def _classify_emotion(self, sentiment_text: str, engagement: Dict) -> str:
        """Classify emotion based on sentiment and controversy."""
        controversy = engagement.get("controversy_ratio", 0)
        
        if controversy > 0.5:
            return "controversial"
        
        text_lower = sentiment_text.lower()
        if any(w in text_lower for w in ["positive", "好评", "喜欢"]):
            return "positive"
        elif any(w in text_lower for w in ["negative", "差评", "批评"]):
            return "negative"
        elif any(w in text_lower for w in ["mixed", "争议"]):
            return "mixed"
        
        return "neutral"
    
    def _generate_implications(self, ir_document: Dict) -> str:
        """Generate implications from IR document."""
        title = ir_document.get("title", "")
        return f"This topic about '{title}' has generated significant social discussion."
    
    def _extract_hook_angles(self, ir_document: Dict, quotes: List[str]) -> List[str]:
        """Extract potential hook angles from IR."""
        hooks = []
        title = ir_document.get("title", "")
        
        if quotes:
            hooks.append(f"Open with quote: {quotes[0][:50]}...")
        if title:
            hooks.append(f"Question hook: Why is '{title[:30]}' trending?")
        
        return hooks[:3]
    
    def _extract_controversy_points(self, blocks: List[Dict]) -> List[str]:
        """Extract controversy points from blocks."""
        points = []
        for block in blocks:
            if block.get("type") == "engineQuote":
                title = block.get("title", "")
                if "dissent" in title.lower() or "debate" in title.lower():
                    for inner in block.get("blocks", []):
                        for inline in inner.get("inlines", []):
                            points.append(inline.get("text", ""))
        return points[:3]
    
    def _extract_references_from_ir(self, ir_document: Dict) -> List[UCSReference]:
        """Extract references from IR document."""
        url = ir_document.get("url", "")
        if url:
            return [UCSReference(
                title=ir_document.get("title", "Source"),
                url=url,
                credibility=self._classify_credibility(url),
                snippet=None
            )]
        return []
    
    # =========================================================================
    # Helper Methods: MiroThinker Extraction
    # =========================================================================
    
    def _extract_findings_from_markdown(self, markdown: str) -> List[str]:
        """Extract key findings from MiroThinker markdown."""
        findings = []
        
        # Look for bullet points under "Key Findings" or similar
        pattern = r'(?:Key Findings|Findings|Main Points)[:\s]*\n((?:\s*[-*]\s+.+\n)+)'
        match = re.search(pattern, markdown, re.IGNORECASE)
        
        if match:
            bullets = match.group(1)
            for line in bullets.split('\n'):
                line = line.strip()
                if line.startswith(('-', '*')):
                    findings.append(line.lstrip('-* '))
        
        return findings[:5]
    
    def _extract_conflicts_from_markdown(self, markdown: str) -> List[str]:
        """Extract conflicting information from markdown."""
        conflicts = []
        
        pattern = r'(?:Conflicting|Disagreement|Debate)[:\s]*\n((?:\s*.+\n)+?)(?=\n#|\Z)'
        match = re.search(pattern, markdown, re.IGNORECASE)
        
        if match:
            text = match.group(1).strip()
            conflicts.append(text[:200])
        
        return conflicts
    
    def _extract_quotes_from_markdown(self, markdown: str) -> List[str]:
        """Extract quoted text from markdown."""
        quotes = []
        
        # Find text in quotes
        pattern = r'"([^"]{20,200})"'
        matches = re.findall(pattern, markdown)
        quotes.extend(matches[:5])
        
        # Find blockquotes
        pattern = r'>\s+(.+)'
        matches = re.findall(pattern, markdown)
        quotes.extend(matches[:3])
        
        return quotes[:5]
    
    def _extract_section(self, markdown: str, section_name: str) -> str:
        """Extract a specific section from markdown."""
        pattern = rf'(?:#{1,3}\s*{section_name})[:\s]*\n((?:.+\n)+?)(?=\n#|\Z)'
        match = re.search(pattern, markdown, re.IGNORECASE)
        
        if match:
            return match.group(1).strip()[:500]
        return ""
    
    def _infer_emotion_from_text(self, text: str) -> str:
        """Infer emotion from text content."""
        text_lower = text.lower()
        
        positive_words = ["success", "breakthrough", "impressive", "great", "好", "赞"]
        negative_words = ["failure", "concern", "problem", "issue", "坏", "差"]
        controversy_words = ["debate", "disagree", "controversy", "争议", "质疑"]
        
        pos_count = sum(1 for w in positive_words if w in text_lower)
        neg_count = sum(1 for w in negative_words if w in text_lower)
        contr_count = sum(1 for w in controversy_words if w in text_lower)
        
        if contr_count > 0:
            return "controversial"
        elif pos_count > neg_count:
            return "positive"
        elif neg_count > pos_count:
            return "negative"
        
        return "neutral"
    
    # =========================================================================
    # Helper Methods: OpenNotebook Extraction
    # =========================================================================
    
    def _extract_citations_from_text(self, text: str) -> List[str]:
        """Extract citations from response text."""
        # Pattern: [Source Name] or (Page X)
        citations = []
        
        pattern = r'\[([^\]]+)\]'
        matches = re.findall(pattern, text)
        citations.extend(matches[:5])
        
        return citations
    
    def _extract_hook_angles_from_text(self, text: str) -> List[str]:
        """Extract potential hooks from text content."""
        hooks = []
        
        # Look for questions
        questions = re.findall(r'([^.!?]*\?)', text)
        hooks.extend(questions[:2])
        
        # Look for surprising statements (starting with "In fact", "Surprisingly", etc.)
        surprise_pattern = r'(?:In fact|Surprisingly|Interestingly|Notably)[,\s]+([^.]+\.)'
        matches = re.findall(surprise_pattern, text, re.IGNORECASE)
        hooks.extend(matches[:2])
        
        return hooks[:3]
    
    # =========================================================================
    # Helper Methods: Common
    # =========================================================================
    
    def _classify_credibility(self, url: str) -> str:
        """Classify URL credibility tier."""
        if not url:
            return "unknown"
        
        url_lower = url.lower()
        
        for domain in self.TIER1_DOMAINS:
            if domain in url_lower:
                return "tier1"
        
        for domain in self.TIER2_DOMAINS:
            if domain in url_lower:
                return "tier2"
        
        return "tier3"
    
    def _parse_number(self, value: str) -> int:
        """Parse number from formatted string (e.g., '1.2K' -> 1200)."""
        try:
            value = str(value).upper().replace(",", "")
            if "K" in value:
                return int(float(value.replace("K", "")) * 1000)
            elif "M" in value:
                return int(float(value.replace("M", "")) * 1000000)
            else:
                return int(float(value))
        except (ValueError, TypeError):
            return 0
    
    def _parse_hours(self, value: str) -> int:
        """Parse hours from formatted string (e.g., '48h' -> 48)."""
        try:
            return int(re.search(r'(\d+)', str(value)).group(1))
        except (AttributeError, ValueError, TypeError):
            return 0


# =========================================================================
# Singleton
# =========================================================================

_normalizer: Optional[IRNormalizer] = None


def get_ir_normalizer() -> IRNormalizer:
    """Get or create the IRNormalizer singleton."""
    global _normalizer
    if _normalizer is None:
        _normalizer = IRNormalizer()
        logger.info("IRNormalizer initialized")
    return _normalizer
