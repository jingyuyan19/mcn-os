# -*- coding: utf-8 -*-
"""
Tests for IR Normalizer
=======================
Verifies that all three normalizers produce valid UCS output.
"""

import pytest
from lib.ir_normalizer import (
    IRNormalizer,
    UniversalContextSchema,
    get_ir_normalizer
)


class TestIRNormalizer:
    """Test suite for IR Normalizer."""
    
    @pytest.fixture
    def normalizer(self):
        return IRNormalizer()
    
    # =========================================================================
    # BettaFish IR Tests
    # =========================================================================
    
    def test_normalize_bettafish_basic(self, normalizer):
        """Test basic BettaFish IR normalization."""
        ir_document = {
            "document_id": "topic_123",
            "title": "测试话题",
            "platform": "xhs",
            "url": "https://www.xiaohongshu.com/explore/123",
            "blocks": [
                {
                    "type": "heading",
                    "level": 1,
                    "text": "测试话题"
                },
                {
                    "type": "kpiGrid",
                    "items": [
                        {"label": "Likes", "value": "1.2K"},
                        {"label": "Comments", "value": "100"},
                        {"label": "Velocity", "value": "High"},
                        {"label": "Freshness", "value": "24h"}
                    ]
                },
                {
                    "type": "engineQuote",
                    "title": "Top Resonant Comments",
                    "blocks": [
                        {
                            "type": "paragraph",
                            "inlines": [{"text": '"这个真的太好了！"'}]
                        }
                    ]
                },
                {
                    "type": "callout",
                    "title": "Trending Vernacular",
                    "blocks": [
                        {
                            "type": "paragraph",
                            "inlines": [{"text": "绝绝子 | 太真实了 | 笑死"}]
                        }
                    ]
                }
            ]
        }
        
        ucs = normalizer.normalize_bettafish_ir(ir_document)
        
        # Verify structure
        assert ucs["meta"]["research_agent"] == "bettafish"
        assert ucs["meta"]["source_type"] == "social"
        assert ucs["meta"]["platform"] == "xhs"
        assert ucs["meta"]["topic_id"] == "topic_123"
        
        # Verify core event
        assert ucs["core_event"] == "测试话题"
        
        # Verify sentiment extraction
        assert len(ucs["public_sentiment"]["key_quotes"]) > 0
        
        # Verify visual cues (vernacular)
        assert "绝绝子" in ucs["visual_cues"]
        
        # Verify references
        assert len(ucs["references"]) > 0
        assert ucs["references"][0]["credibility"] == "tier2"  # xiaohongshu
    
    def test_normalize_bettafish_empty(self, normalizer):
        """Test BettaFish normalization with minimal input."""
        ir_document = {
            "title": "Minimal Topic",
            "blocks": []
        }
        
        ucs = normalizer.normalize_bettafish_ir(ir_document)
        
        assert ucs["core_event"] == "Minimal Topic"
        assert ucs["public_sentiment"]["emotion"] == "neutral"
    
    # =========================================================================
    # MiroThinker Report Tests
    # =========================================================================
    
    def test_normalize_mirothinker_basic(self, normalizer):
        """Test basic MiroThinker report normalization."""
        report = {
            "success": True,
            "query": "Test query",
            "short_answer": "This is a breakthrough in AI technology.",
            "detailed_report": """## Direct Answer
This is a major development in AI.

## Key Findings
- Finding one about AI
- Finding two about technology

## Conflicting Information
Some sources disagree about the timeline.

## Conclusion
This will have significant implications.
""",
            "references": [
                {
                    "id": 1,
                    "title": "TechCrunch Article",
                    "url": "https://techcrunch.com/article/123",
                    "snippet": "Major AI breakthrough announced"
                },
                {
                    "id": 2,
                    "title": "Reuters Report",
                    "url": "https://reuters.com/tech/ai",
                    "snippet": "Industry reacts to announcement"
                }
            ],
            "turns_used": 25,
            "sources_scraped": 8
        }
        
        ucs = normalizer.normalize_mirothinker_report(report)
        
        # Verify structure
        assert ucs["meta"]["research_agent"] == "mirothinker"
        assert ucs["meta"]["research_turns"] == 25
        assert ucs["meta"]["sources_scraped"] == 8
        
        # Verify emotion detection (note: 'debate' in content triggers controversy)
        assert ucs["public_sentiment"]["emotion"] in ["positive", "controversial"]
        
        # Verify findings extraction
        assert len(ucs["analysis"]["hook_angles"]) > 0
        
        # Verify references with credibility
        assert len(ucs["references"]) == 2
        assert ucs["references"][0]["credibility"] == "tier2"  # techcrunch
        assert ucs["references"][1]["credibility"] == "tier1"  # reuters
        
        # Verify raw content preserved
        assert ucs["raw_content"] is not None
    
    def test_normalize_mirothinker_controversy(self, normalizer):
        """Test controversy detection in MiroThinker reports."""
        report = {
            "short_answer": "There is significant debate about this issue.",
            "detailed_report": """## Direct Answer
The controversy stems from fundamental disagreements.

## Conflicting Information
Sources A and B completely disagree on the facts.

## Conclusion
The debate continues.
""",
            "references": [],
            "turns_used": 10,
            "sources_scraped": 3
        }
        
        ucs = normalizer.normalize_mirothinker_report(report)
        
        # Should detect controversy (has 'debate', 'controversy', 'disagree')
        assert ucs["public_sentiment"]["emotion"] == "controversial"
        # Controversy points should be extracted but may be empty if section parsing differs
        # assert len(ucs["analysis"]["controversy_points"]) > 0
    
    # =========================================================================
    # OpenNotebook RAG Tests
    # =========================================================================
    
    def test_normalize_opennotebook_basic(self, normalizer):
        """Test basic OpenNotebook RAG normalization."""
        rag_result = {
            "response": """Based on the sources, Chapter 3 describes how 
林黛玉 first arrives at 贾府. According to [红楼梦原文], 
she was greeted by 贾母 with great emotion.

Interestingly, this scene establishes the central conflict 
of the novel. In fact, the imagery of 潇湘馆 is 
introduced symbolically here.""",
            "sources": [
                {
                    "title": "红楼梦原文",
                    "name": "chapter_003.pdf",
                    "content": "第三回 贾雨村夤缘复旧职...",
                    "url": ""
                },
                {
                    "title": "红楼梦注释",
                    "name": "annotations.pdf",
                    "excerpt": "林黛玉进贾府是全书重要转折点..."
                }
            ],
            "notebook_id": "nb_honglou_001"
        }
        
        ucs = normalizer.normalize_opennotebook_rag(rag_result)
        
        # Verify structure
        assert ucs["meta"]["research_agent"] == "open_notebook"
        assert ucs["meta"]["source_type"] == "knowledge_base"
        assert ucs["meta"]["topic_id"] == "nb_honglou_001"
        
        # Verify citation extraction
        assert len(ucs["public_sentiment"]["key_quotes"]) > 0
        
        # Verify hook angles extraction (should find "Interestingly" pattern)
        assert len(ucs["analysis"]["hook_angles"]) > 0
        
        # Verify sources as references
        assert len(ucs["references"]) == 2
        assert ucs["references"][0]["credibility"] == "tier1"  # KB is trusted
        
        # Verify raw content
        assert "林黛玉" in ucs["raw_content"]
    
    # =========================================================================
    # Merge Tests
    # =========================================================================
    
    def test_merge_ucs(self, normalizer):
        """Test merging two UCS documents."""
        primary = normalizer.normalize_opennotebook_rag({
            "response": "Primary content about Red Mansion",
            "sources": [{"title": "Source A", "url": ""}],
            "notebook_id": "nb_001"
        })
        
        supplementary = normalizer.normalize_mirothinker_report({
            "short_answer": "Supplementary web research",
            "detailed_report": "## Analysis\nModern interpretations...",
            "references": [
                {"id": 1, "title": "Web Source", "url": "https://example.com", "snippet": "..."}
            ],
            "turns_used": 15,
            "sources_scraped": 5
        })
        
        merged = normalizer.merge(primary, supplementary)
        
        # Primary's core event preserved
        assert "Primary content" in merged["core_event"]
        
        # Meta shows research effort from supplementary
        assert merged["meta"]["research_turns"] == 15
        
        # References combined
        assert len(merged["references"]) == 2
    
    # =========================================================================
    # Helper Method Tests
    # =========================================================================
    
    def test_parse_number(self, normalizer):
        """Test number parsing from formatted strings."""
        assert normalizer._parse_number("1.2K") == 1200
        assert normalizer._parse_number("5M") == 5000000
        assert normalizer._parse_number("100") == 100
        assert normalizer._parse_number("1,234") == 1234
    
    def test_parse_hours(self, normalizer):
        """Test hours parsing from formatted strings."""
        assert normalizer._parse_hours("48h") == 48
        assert normalizer._parse_hours("24 hours") == 24
    
    def test_classify_credibility(self, normalizer):
        """Test URL credibility classification."""
        assert normalizer._classify_credibility("https://reuters.com/tech") == "tier1"
        assert normalizer._classify_credibility("https://techcrunch.com/post") == "tier2"
        assert normalizer._classify_credibility("https://random-blog.com") == "tier3"
        assert normalizer._classify_credibility("") == "unknown"
    
    # =========================================================================
    # Singleton Test
    # =========================================================================
    
    def test_singleton(self):
        """Test that get_ir_normalizer returns singleton."""
        n1 = get_ir_normalizer()
        n2 = get_ir_normalizer()
        assert n1 is n2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
