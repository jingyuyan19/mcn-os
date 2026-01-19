# -*- coding: utf-8 -*-
"""
ReportEngine Integration
========================
Wrapper for BettaFish ReportEngine providing GraphRAG knowledge graph capabilities.

Key Features:
- Knowledge graph construction from research data
- Graph-based querying for contextual insights
- Cross-reference discovery across topics
- Enhanced context for storyboard generation

Usage:
    from lib.report_engine import get_report_engine
    
    re = get_report_engine()
    
    # Build a knowledge graph from topic research
    graph = re.build_graph_from_topic(topic_id="123", platform="xhs")
    
    # Get graph summary for LLM context
    context = re.get_graph_context_for_llm()
"""

import logging
import sys
import os
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger("ReportEngine")

# Add BettaFish to path
BETTAFISH_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../external/BettaFish')
)


class ReportEngineWrapper:
    """
    Wrapper for BettaFish ReportEngine GraphRAG capabilities.
    
    Provides:
    - Knowledge graph construction from CCO/IR data
    - Graph-based semantic querying
    - Context generation for LLM prompts
    """
    
    def __init__(self):
        """Initialize ReportEngine wrapper."""
        self._graph = None
        self._bettafish_client = None
        self._modules_loaded = False
        logger.info("ReportEngineWrapper initialized")
    
    def _load_graphrag_modules(self):
        """Lazy load GraphRAG modules."""
        if self._modules_loaded:
            return
            
        # Load BettaFish .env
        from dotenv import load_dotenv
        bettafish_env = os.path.join(BETTAFISH_PATH, '.env')
        if os.path.exists(bettafish_env):
            load_dotenv(bettafish_env)
        
        if BETTAFISH_PATH not in sys.path:
            sys.path.insert(0, BETTAFISH_PATH)
        
        self._modules_loaded = True
    
    def _get_bettafish_client(self):
        """Get our working bettafish client."""
        if self._bettafish_client is None:
            from lib.bettafish_client import BettaFishClient
            self._bettafish_client = BettaFishClient()
        return self._bettafish_client
    
    def build_graph_from_topic(
        self, 
        topic_id: str, 
        platform: str
    ) -> Dict:
        """
        Build a knowledge graph from a topic's research data.
        
        Creates nodes for:
        - Topic (central node)
        - Comments (from top resonant)
        - Keywords (from vernacular cloud)
        - Sentiment
        
        Args:
            topic_id: Topic ID
            platform: Platform name
            
        Returns:
            Graph summary dict
        """
        try:
            self._load_graphrag_modules()
            from ReportEngine.graphrag import Graph
            
            # Get topic data
            bf = self._get_bettafish_client()
            cco = bf.get_topic_cco(topic_id, platform)
            
            # Initialize graph
            self._graph = Graph()
            
            # Create central topic node using correct API
            topic_node = self._graph.add_node(
                node_type='topic',
                name=cco.get('title', 'Unknown Topic'),
                node_id=f"topic_{topic_id}",
                platform=platform,
                author=cco.get('author', ''),
                created=datetime.now().isoformat()
            )
            
            # Add comment nodes
            vox = cco.get('vox_populi', {})
            for i, comment in enumerate(vox.get('top_resonant', [])[:10]):
                comment_text = comment.get('text', '')[:100]
                if comment_text:
                    comment_node = self._graph.add_node(
                        node_type='comment',
                        name=comment_text,
                        node_id=f"comment_{topic_id}_{i}",
                        likes=comment.get('likes', 0),
                        full_text=comment.get('text', '')
                    )
                    self._graph.add_edge(topic_node, comment_node, 'has_comment')
            
            # Add keyword nodes from vernacular cloud
            for keyword in vox.get('vernacular_cloud', [])[:15]:
                keyword_node = self._graph.add_node(
                    node_type='keyword',
                    name=keyword,
                    node_id=f"keyword_{keyword}",
                    source='vernacular_cloud'
                )
                self._graph.add_edge(topic_node, keyword_node, 'has_keyword')
            
            # Add sentiment node if available
            sentiment = cco.get('sentiment', {})
            if sentiment.get('dominant'):
                sentiment_node = self._graph.add_node(
                    node_type='sentiment',
                    name=sentiment.get('dominant', 'neutral'),
                    node_id=f"sentiment_{topic_id}",
                    distribution=str(sentiment.get('distribution', {})),
                    confidence=sentiment.get('average_confidence', 0)
                )
                self._graph.add_edge(topic_node, sentiment_node, 'has_sentiment')
            
            stats = self._graph.get_stats()
            logger.info(f"Built graph for topic {topic_id}: {stats}")
            
            return {
                "success": True,
                "topic_id": topic_id,
                "platform": platform,
                "nodes": stats.get('total_nodes', 0),
                "edges": stats.get('total_edges', 0),
                "node_types": {k: v for k, v in stats.items() 
                             if k not in ['total_nodes', 'total_edges']}
            }
            
        except Exception as e:
            logger.error(f"Failed to build graph: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
    
    def get_graph_summary(self) -> Dict:
        """
        Get a summary of the current graph.
        
        Returns:
            Summary dict with node counts by type, etc.
        """
        if self._graph is None:
            return {"error": "No graph loaded."}
        
        return self._graph.get_summary()
    
    def get_graph_context_for_llm(self, max_chars: int = 2000) -> str:
        """
        Generate a text summary of the graph suitable for LLM context.
        
        This can be injected into storyboard generation prompts.
        
        Args:
            max_chars: Maximum characters for output
            
        Returns:
            Text summary of graph knowledge
        """
        if self._graph is None:
            return "No knowledge graph available."
        
        try:
            summary = self._graph.get_summary()
            stats = self._graph.get_stats()
            
            lines = [
                f"# Knowledge Graph Summary",
                f"Total Nodes: {stats.get('total_nodes', 0)}",
                f"Total Edges: {stats.get('total_edges', 0)}",
                "",
                "## Node Types:"
            ]
            
            for key, value in stats.items():
                if key not in ['total_nodes', 'total_edges']:
                    lines.append(f"- {key}: {value}")
            
            # Add key keywords
            keywords = [n.name for n in self._graph.get_nodes_by_type('keyword')]
            if keywords:
                lines.append("")
                lines.append(f"## Key Keywords: {', '.join(keywords[:15])}")
            
            # Add top comments
            comments = [n.name for n in self._graph.get_nodes_by_type('comment')]
            if comments:
                lines.append("")
                lines.append("## Top Comments:")
                for c in comments[:5]:
                    lines.append(f"- {c[:60]}...")
            
            text = "\n".join(lines)
            
            # Truncate if too long
            if len(text) > max_chars:
                text = text[:max_chars] + "\n... (truncated)"
            
            return text
            
        except Exception as e:
            logger.error(f"Failed to generate graph context: {e}")
            return f"Error generating graph context: {e}"
    
    def get_keywords(self) -> List[str]:
        """Get all keywords from the graph."""
        if self._graph is None:
            return []
        return [n.name for n in self._graph.get_nodes_by_type('keyword')]
    
    def get_top_comments(self, limit: int = 5) -> List[Dict]:
        """Get top comments from the graph."""
        if self._graph is None:
            return []
        
        comments = []
        for n in self._graph.get_nodes_by_type('comment')[:limit]:
            comments.append({
                "text": n.name,
                "likes": n.get('likes', 0)
            })
        return comments
    
    def list_templates(self) -> List[str]:
        """
        List available report templates.
        
        Returns:
            List of template names (without .md extension)
        """
        try:
            template_dir = os.path.join(BETTAFISH_PATH, 'ReportEngine', 'report_template')
            if not os.path.exists(template_dir):
                logger.warning(f"Template directory not found: {template_dir}")
                return []
            
            templates = []
            for f in os.listdir(template_dir):
                if f.endswith('.md'):
                    templates.append(f[:-3])  # Remove .md extension
            
            logger.info(f"Found {len(templates)} report templates")
            return sorted(templates)
            
        except Exception as e:
            logger.error(f"Failed to list templates: {e}")
            return []
    
    def generate_report(
        self,
        topic_data: Dict,
        template_name: str = None,
        output_format: str = "markdown"
    ) -> Dict:
        """
        Generate a professional report using BettaFish templates.
        
        Args:
            topic_data: Topic data including CCO, sentiment, citations
            template_name: Template to use (None for auto-select)
            output_format: "markdown", "html", or "both"
            
        Returns:
            {
                "success": True,
                "markdown": "...",
                "html": "..." (if requested),
                "template_used": "..."
            }
        """
        try:
            # Auto-select template if not specified
            if not template_name:
                templates = self.list_templates()
                template_name = templates[0] if templates else "企业品牌声誉分析报告"
            
            # Load template
            template_path = os.path.join(
                BETTAFISH_PATH, 'ReportEngine', 'report_template', 
                f"{template_name}.md"
            )
            
            if os.path.exists(template_path):
                with open(template_path, 'r', encoding='utf-8') as f:
                    template_content = f.read()
            else:
                template_content = self._get_default_template()
            
            # Fill template with data
            report_md = self._fill_template(template_content, topic_data)
            
            result = {
                "success": True,
                "markdown": report_md,
                "template_used": template_name
            }
            
            # Render HTML if requested
            if output_format in ["html", "both"]:
                result["html"] = self._render_markdown_to_html(report_md)
            
            logger.info(f"Report generated using template: {template_name}")
            return result
            
        except Exception as e:
            import traceback
            logger.error(f"Report generation failed: {e}\n{traceback.format_exc()}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_default_template(self) -> str:
        """Get default report template."""
        return """# {title}

## 执行摘要

{summary}

## 数据来源

- 分析时间: {timestamp}
- 数据范围: {platform}
- 记录数量: {record_count}

## 情感分析

{sentiment_section}

## 热门关键词

{keywords_section}

## 热门评论

{comments_section}

## 结论与建议

{conclusions}

---

*本报告由MCN OS自动生成*
"""
    
    def _fill_template(self, template: str, data: Dict) -> str:
        """Fill template with topic data."""
        from datetime import datetime
        
        # Extract data with defaults
        title = data.get('title', '舆情分析报告')
        platform = data.get('platform', 'unknown')
        
        # Summary
        summary = data.get('summary', '')
        if not summary and 'ir' in data:
            summary = data['ir'].get('executive_summary', '待分析')
        
        # Sentiment
        sentiment = data.get('sentiment', {})
        if sentiment:
            sentiment_section = f"""
- 主导情绪: {sentiment.get('dominant', 'unknown')}
- 正面比例: {sentiment.get('positive_ratio', 0):.1%}
- 负面比例: {sentiment.get('negative_ratio', 0):.1%}
"""
        else:
            sentiment_section = "情感数据暂不可用"
        
        # Keywords
        keywords = data.get('keywords', [])
        if keywords:
            keywords_section = ", ".join(keywords[:20])
        else:
            keywords_section = "关键词数据暂不可用"
        
        # Comments
        comments = data.get('top_comments', [])
        if comments:
            comments_section = "\n".join([f"- {c.get('text', '')[:80]}..." for c in comments[:5]])
        else:
            comments_section = "评论数据暂不可用"
        
        # Conclusions
        conclusions = data.get('conclusions', '基于以上分析，建议进一步深入研究。')
        
        # Fill template
        filled = template.format(
            title=title,
            summary=summary or '待分析',
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
            platform=platform,
            record_count=data.get('record_count', 0),
            sentiment_section=sentiment_section,
            keywords_section=keywords_section,
            comments_section=comments_section,
            conclusions=conclusions
        )
        
        return filled
    
    def _render_markdown_to_html(self, markdown_text: str) -> str:
        """Render markdown to HTML."""
        try:
            import markdown
            html = markdown.markdown(markdown_text, extensions=['tables', 'fenced_code'])
            
            # Wrap in basic HTML structure
            full_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>舆情分析报告</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.6; }}
        h1, h2, h3 {{ color: #333; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f4f4f4; }}
        code {{ background-color: #f4f4f4; padding: 2px 6px; border-radius: 3px; }}
    </style>
</head>
<body>
{html}
</body>
</html>"""
            return full_html
            
        except ImportError:
            logger.warning("markdown library not available, returning raw markdown")
            return f"<pre>{markdown_text}</pre>"


# Singleton
_engine: Optional[ReportEngineWrapper] = None


def get_report_engine() -> ReportEngineWrapper:
    """Get or create the ReportEngine wrapper singleton."""
    global _engine
    if _engine is None:
        _engine = ReportEngineWrapper()
    return _engine
