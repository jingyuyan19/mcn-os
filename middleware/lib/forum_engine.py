# -*- coding: utf-8 -*-
"""
ForumEngine Integration
=======================
Wrapper for BettaFish ForumEngine providing multi-agent LLM debate/discussion.

Key Features:
- Simulates multi-agent discussion on a topic
- LLM host synthesizes and moderates viewpoints
- Generates structured analysis with timeline, viewpoints, trends
- Produces follow-up questions for deeper analysis

Use Cases:
- Controversial topic analysis
- Multi-perspective research synthesis
- Generating balanced viewpoints on complex issues

Usage:
    from lib.forum_engine import get_forum_engine
    
    fe = get_forum_engine()
    
    # Run a multi-agent discussion on a topic
    result = fe.discuss_topic(topic_id="123", platform="xhs")
    
    # Or provide custom agent inputs
    result = fe.host_discussion(agent_speeches=[
        {"speaker": "INSIGHT", "content": "Database analysis shows..."},
        {"speaker": "MEDIA", "content": "Media coverage indicates..."},
        {"speaker": "QUERY", "content": "Web search reveals..."}
    ])
"""

import logging
import sys
import os
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger("ForumEngine")

# Add BettaFish to path
BETTAFISH_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../external/BettaFish')
)


class ForumEngineWrapper:
    """
    Wrapper for BettaFish ForumEngine (LLM-moderated multi-agent discussion).
    
    Provides:
    - Multi-agent discussion simulation
    - LLM host moderation and synthesis
    - Structured analysis output
    """
    
    def __init__(self):
        """Initialize ForumEngine wrapper."""
        self._forum_host = None
        self._bettafish_client = None
        self._insight_engine = None
        self._query_engine = None
        self._media_engine = None
        logger.info("ForumEngineWrapper initialized")
    
    def _load_forum_host(self):
        """Lazy load ForumHost."""
        if self._forum_host is None:
            # Load BettaFish .env
            from dotenv import load_dotenv
            bettafish_env = os.path.join(BETTAFISH_PATH, '.env')
            if os.path.exists(bettafish_env):
                load_dotenv(bettafish_env)
                logger.info(f"Loaded BettaFish config from {bettafish_env}")
            
            if BETTAFISH_PATH not in sys.path:
                sys.path.insert(0, BETTAFISH_PATH)
            
            try:
                from ForumEngine.llm_host import ForumHost
                self._forum_host = ForumHost()
                logger.info("ForumHost loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load ForumHost: {e}")
                raise
        return self._forum_host
    
    def _get_bettafish_client(self):
        """Get our working bettafish client."""
        if self._bettafish_client is None:
            from lib.bettafish_client import BettaFishClient
            self._bettafish_client = BettaFishClient()
        return self._bettafish_client
    
    def _get_insight_engine(self):
        """Get InsightEngine for INSIGHT agent."""
        if self._insight_engine is None:
            from lib.insight_engine import get_insight_engine
            self._insight_engine = get_insight_engine()
        return self._insight_engine
    
    def _get_query_engine(self):
        """Get QueryEngine for QUERY agent."""
        if self._query_engine is None:
            from lib.query_engine import get_query_engine
            self._query_engine = get_query_engine()
        return self._query_engine
    
    def _get_media_engine(self):
        """Get MediaEngine for MEDIA agent."""
        if self._media_engine is None:
            from lib.media_engine import get_media_engine
            self._media_engine = get_media_engine()
        return self._media_engine
    
    def _format_agent_log(self, speaker: str, content: str) -> str:
        """Format a log line for forum discussion."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        # Escape newlines for log format
        content_escaped = content.replace('\n', '\\n')
        return f"[{timestamp}] [{speaker}] {content_escaped}"
    
    def host_discussion(self, agent_speeches: List[Dict]) -> Dict:
        """
        Run LLM host to moderate a discussion.
        
        Args:
            agent_speeches: List of dicts with 'speaker' and 'content'
                - speaker: INSIGHT, MEDIA, or QUERY
                - content: The agent's contribution
                
        Returns:
            Dict with host synthesis and structured analysis
        """
        try:
            forum_host = self._load_forum_host()
            
            # Format speeches as log lines
            log_lines = []
            for speech in agent_speeches:
                speaker = speech.get('speaker', 'UNKNOWN')
                content = speech.get('content', '')
                log_line = self._format_agent_log(speaker, content)
                log_lines.append(log_line)
            
            # Generate host response
            host_speech = forum_host.generate_host_speech(log_lines)
            
            if host_speech:
                return {
                    "success": True,
                    "host_analysis": host_speech,
                    "agent_count": len(agent_speeches),
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "success": False,
                    "error": "Host failed to generate response"
                }
                
        except Exception as e:
            logger.error(f"Discussion failed: {e}")
            return {"success": False, "error": str(e)}
    
    def host_discussion_with_debate(
        self, 
        agent_speeches: List[Dict],
        detect_conflicts: bool = True
    ) -> Dict:
        """
        Run LLM host with conflict detection and debate.
        
        When agents disagree, this method:
        1. Detects conflicting claims
        2. Adds debate prompts to reconcile
        3. Generates uncertainty-aware synthesis
        
        Args:
            agent_speeches: List of dicts with 'speaker' and 'content'
            detect_conflicts: Whether to detect and highlight conflicts
            
        Returns:
            Dict with analysis, conflicts detected, and confidence level
        """
        try:
            # First detect any conflicts
            conflicts = []
            if detect_conflicts and len(agent_speeches) >= 2:
                conflicts = self._detect_conflicts(agent_speeches)
            
            # If conflicts found, add debate prompts
            if conflicts:
                debate_prompt = self._build_debate_prompt(conflicts)
                agent_speeches.append({
                    "speaker": "MODERATOR",
                    "content": debate_prompt
                })
            
            # Run host discussion
            result = self.host_discussion(agent_speeches)
            
            # Add conflict metadata
            result["conflicts_detected"] = len(conflicts)
            result["conflicts"] = conflicts
            result["confidence"] = "high" if not conflicts else "medium"
            
            if conflicts:
                result["uncertainty_note"] = (
                    f"注意: 发现 {len(conflicts)} 处数据冲突。"
                    "分析结论已考虑多方观点，但建议进一步验证。"
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Debate discussion failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _detect_conflicts(self, agent_speeches: List[Dict]) -> List[Dict]:
        """
        Detect conflicting claims between agents.
        
        Looks for:
        - Opposing sentiment (positive vs negative)
        - Contradictory trends (up vs down)
        - Conflicting numbers
        """
        conflicts = []
        
        # Extract content from each speaker
        contents = {}
        for speech in agent_speeches:
            speaker = speech.get('speaker', 'UNKNOWN')
            content = speech.get('content', '').lower()
            contents[speaker] = content
        
        # Check for sentiment conflicts
        positive_words = ['正面', '积极', '好评', 'positive', '上涨', '增长', '热门']
        negative_words = ['负面', '消极', '差评', 'negative', '下跌', '下降', '冷门']
        
        positive_agents = []
        negative_agents = []
        
        for speaker, content in contents.items():
            pos_count = sum(1 for w in positive_words if w in content)
            neg_count = sum(1 for w in negative_words if w in content)
            
            if pos_count > neg_count + 1:
                positive_agents.append(speaker)
            elif neg_count > pos_count + 1:
                negative_agents.append(speaker)
        
        if positive_agents and negative_agents:
            conflicts.append({
                "type": "sentiment_conflict",
                "description": f"{', '.join(positive_agents)} 显示正面趋势，"
                              f"但 {', '.join(negative_agents)} 显示负面趋势",
                "agents_positive": positive_agents,
                "agents_negative": negative_agents
            })
        
        # Check for data source conflicts
        if 'INSIGHT' in contents and 'QUERY' in contents:
            # Database vs web might have different recency
            if '数据库' in contents.get('INSIGHT', '') and '最新' in contents.get('QUERY', ''):
                conflicts.append({
                    "type": "recency_conflict",
                    "description": "数据库数据可能滞后于实时网络搜索",
                    "agents": ["INSIGHT", "QUERY"]
                })
        
        return conflicts
    
    def _build_debate_prompt(self, conflicts: List[Dict]) -> str:
        """Build a prompt asking agents to reconcile conflicts."""
        lines = [
            "【主持人提醒】检测到以下数据冲突，请各Agent注意:",
            ""
        ]
        
        for i, conflict in enumerate(conflicts, 1):
            lines.append(f"{i}. {conflict['description']}")
        
        lines.extend([
            "",
            "请在综合分析时:",
            "- 明确标注不确定性",
            "- 解释可能的冲突原因",
            "- 给出条件性结论（如：'如果A则X，如果B则Y'）"
        ])
        
        return "\n".join(lines)
    
    def discuss_topic(
        self, 
        topic_id: str, 
        platform: str,
        include_web_search: bool = True
    ) -> Dict:
        """
        Run a full multi-agent discussion on a topic.
        
        Automatically gathers perspectives from:
        - INSIGHT: Database analysis (CCO, sentiment)
        - MEDIA: Multimodal search (Bocha)
        - QUERY: Web/news search (Tavily)
        
        Then synthesizes via LLM host.
        
        Args:
            topic_id: Topic ID
            platform: Platform name
            include_web_search: Whether to include web search agents
            
        Returns:
            Dict with full discussion results
        """
        try:
            # Gather agent contributions
            agent_speeches = []
            
            # INSIGHT Agent: Database analysis
            bf = self._get_bettafish_client()
            cco = bf.get_topic_cco(topic_id, platform)
            
            insight_content = self._build_insight_speech(cco)
            agent_speeches.append({
                "speaker": "INSIGHT",
                "content": insight_content
            })
            
            if include_web_search:
                topic_title = cco.get('title', '')
                
                # QUERY Agent: Tavily web search
                try:
                    qe = self._get_query_engine()
                    query_result = qe.search_news(topic_title, max_results=5)
                    query_content = self._build_query_speech(query_result)
                    agent_speeches.append({
                        "speaker": "QUERY",
                        "content": query_content
                    })
                except Exception as e:
                    logger.warning(f"QUERY agent failed: {e}")
                
                # MEDIA Agent: Bocha multimodal search
                try:
                    me = self._get_media_engine()
                    media_result = me.search(topic_title, max_results=5)
                    media_content = self._build_media_speech(media_result)
                    agent_speeches.append({
                        "speaker": "MEDIA",
                        "content": media_content
                    })
                except Exception as e:
                    logger.warning(f"MEDIA agent failed: {e}")
            
            # Run host discussion
            result = self.host_discussion(agent_speeches)
            
            # Add topic context
            result["topic_id"] = topic_id
            result["platform"] = platform
            result["topic_title"] = cco.get('title', '')
            result["agent_speeches"] = agent_speeches
            
            return result
            
        except Exception as e:
            logger.error(f"Topic discussion failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _build_insight_speech(self, cco: Dict) -> str:
        """Build INSIGHT agent's speech from CCO data."""
        lines = [
            f"话题标题: {cco.get('title', 'Unknown')}",
            f"平台: {cco.get('platform', 'Unknown')}",
            f"作者: {cco.get('author', 'Unknown')}",
            "",
            "互动数据分析:"
        ]
        
        kpis = cco.get('kpis', {})
        lines.append(f"- 点赞数: {kpis.get('likes', 0)}")
        lines.append(f"- 评论数: {kpis.get('comments', 0)}")
        lines.append(f"- 收藏数: {kpis.get('collects', 0)}")
        lines.append(f"- 分享数: {kpis.get('shares', 0)}")
        
        vox = cco.get('vox_populi', {})
        
        # Vernacular
        keywords = vox.get('vernacular_cloud', [])[:10]
        if keywords:
            lines.append("")
            lines.append(f"热门关键词: {', '.join(keywords)}")
        
        # Sentiment
        sentiment = cco.get('sentiment', {})
        if sentiment.get('dominant'):
            lines.append("")
            lines.append(f"情感分析: 主导情绪为 {sentiment.get('dominant')}")
        
        # Top comments
        top_comments = vox.get('top_resonant', [])[:3]
        if top_comments:
            lines.append("")
            lines.append("高共鸣评论:")
            for c in top_comments:
                text = c.get('text', '')[:80]
                lines.append(f"  - {text}...")
        
        return "\n".join(lines)
    
    def _build_query_speech(self, result: Dict) -> str:
        """Build QUERY agent's speech from Tavily results."""
        lines = ["Web搜索分析结果:"]
        
        for item in result.get('results', [])[:5]:
            title = item.get('title', '')[:50]
            snippet = item.get('content', '')[:100]
            lines.append(f"- {title}")
            if snippet:
                lines.append(f"  摘要: {snippet}...")
        
        if not result.get('results'):
            lines.append("未找到相关网页结果")
        
        return "\n".join(lines)
    
    def _build_media_speech(self, result: Dict) -> str:
        """Build MEDIA agent's speech from Bocha results."""
        lines = ["多模态搜索分析:"]
        
        # AI summary
        answer = result.get('answer')
        if answer:
            lines.append(f"AI综述: {answer[:200]}...")
        
        # Webpages
        for item in result.get('webpages', [])[:3]:
            title = item.get('title', '')[:50]
            lines.append(f"- {title}")
        
        # Modal cards (structured data)
        cards = result.get('modal_cards', [])
        if cards:
            lines.append("")
            lines.append(f"发现 {len(cards)} 个结构化数据卡片")
        
        return "\n".join(lines)
    
    def deep_discuss(
        self, 
        query: str,
        include_all_engines: bool = True,
        parallel: bool = True,
        max_rounds: int = 1
    ) -> Dict:
        """
        Run full multi-agent deep research discussion.
        
        This implements the FULL BettaFish workflow:
        1. Agents run deep_research() in PARALLEL
        2. Reports are shared in the forum
        3. LLM host synthesizes and moderates
        4. (Optional) Multi-round iterations
        
        Uses Antigravity Manager (zero LLM cost).
        
        Args:
            query: Research query
            include_all_engines: Use all 3 engines (Insight/Query/Media)
            parallel: Run agents in parallel (3x faster)
            max_rounds: Number of forum discussion rounds
            
        Returns:
            {
                "success": True,
                "host_analysis": "Synthesized analysis...",
                "agent_reports": {...},
                "rounds_completed": N
            }
        """
        if max_rounds > 1:
            return self._deep_discuss_iterative(
                query, include_all_engines, max_rounds
            )
        
        if parallel and include_all_engines:
            return self._deep_discuss_parallel(query)
        else:
            return self._deep_discuss_sequential(query, include_all_engines)
    
    def _deep_discuss_parallel(self, query: str) -> Dict:
        """
        Run all 3 agents in PARALLEL for 3x speedup.
        
        Implements Step 2 of BettaFish workflow: 并行启动
        """
        import concurrent.futures
        
        logger.info(f"Starting PARALLEL deep discussion: {query}")
        
        agent_reports = {}
        agent_speeches = []
        
        # Get engine references
        ie = self._get_insight_engine()
        qe = self._get_query_engine()
        me = self._get_media_engine()
        
        # Run all 3 agents in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(ie.deep_research, query): "insight",
                executor.submit(qe.deep_research, query): "query",
                executor.submit(me.deep_research, query): "media"
            }
            
            for future in concurrent.futures.as_completed(futures):
                agent_name = futures[future]
                try:
                    result = future.result(timeout=1800)  # 30 min timeout per agent
                    if result.get("success"):
                        report = result.get("report", "")
                        agent_reports[agent_name] = report
                        
                        speaker_map = {
                            "insight": ("INSIGHT", "私有数据库深度分析"),
                            "query": ("QUERY", "Web广度搜索深度分析"),
                            "media": ("MEDIA", "多模态内容深度分析")
                        }
                        speaker, prefix = speaker_map[agent_name]
                        agent_speeches.append({
                            "speaker": speaker,
                            "content": f"{prefix}:\n{report[:2000]}"
                        })
                        logger.info(f"{agent_name.upper()} deep research complete (parallel)")
                except Exception as e:
                    logger.warning(f"{agent_name.upper()} deep research failed: {e}")
        
        # Forum host synthesis
        if agent_speeches:
            result = self.host_discussion_with_debate(agent_speeches)
            result["agent_reports"] = agent_reports
            result["query"] = query
            result["execution_mode"] = "parallel"
            logger.info(f"Parallel deep discussion complete: {query}")
            return result
        else:
            return {
                "success": False,
                "error": "No agent research completed successfully"
            }
    
    def _deep_discuss_sequential(
        self, query: str, include_all_engines: bool
    ) -> Dict:
        """Sequential execution (original implementation)."""
        agent_speeches = []
        agent_reports = {}
        
        logger.info(f"Starting sequential deep discussion: {query}")
        
        # INSIGHT Agent
        try:
            ie = self._get_insight_engine()
            insight_result = ie.deep_research(query)
            if insight_result.get("success"):
                report = insight_result.get("report", "")
                agent_reports["insight"] = report
                agent_speeches.append({
                    "speaker": "INSIGHT",
                    "content": f"私有数据库深度分析:\n{report[:2000]}"
                })
        except Exception as e:
            logger.warning(f"INSIGHT failed: {e}")
        
        if include_all_engines:
            # QUERY Agent
            try:
                qe = self._get_query_engine()
                query_result = qe.deep_research(query)
                if query_result.get("success"):
                    report = query_result.get("report", "")
                    agent_reports["query"] = report
                    agent_speeches.append({
                        "speaker": "QUERY",
                        "content": f"Web广度搜索深度分析:\n{report[:2000]}"
                    })
            except Exception as e:
                logger.warning(f"QUERY failed: {e}")
            
            # MEDIA Agent
            try:
                me = self._get_media_engine()
                media_result = me.deep_research(query)
                if media_result.get("success"):
                    report = media_result.get("report", "")
                    agent_reports["media"] = report
                    agent_speeches.append({
                        "speaker": "MEDIA",
                        "content": f"多模态内容深度分析:\n{report[:2000]}"
                    })
            except Exception as e:
                logger.warning(f"MEDIA failed: {e}")
        
        if agent_speeches:
            result = self.host_discussion_with_debate(agent_speeches)
            result["agent_reports"] = agent_reports
            result["query"] = query
            result["execution_mode"] = "sequential"
            return result
        else:
            return {"success": False, "error": "No agent research completed"}
    
    def _deep_discuss_iterative(
        self, 
        query: str,
        include_all_engines: bool = True,
        max_rounds: int = 3
    ) -> Dict:
        """
        Multi-round forum discussion with iterative refinement.
        
        Implements Steps 5-N of BettaFish workflow:
        5.1 深度研究: Agents research based on forum guidance
        5.2 论坛协作: ForumEngine generates host guidance
        5.3 交流融合: Agents adjust based on discussion
        
        Each round:
        1. Agents research (with forum guidance from previous round)
        2. Forum synthesizes findings
        3. If more research needed, refine query and continue
        """
        logger.info(f"Starting ITERATIVE discussion ({max_rounds} rounds): {query}")
        
        all_reports = []
        current_query = query
        forum_guidance = None
        
        for round_num in range(1, max_rounds + 1):
            logger.info(f"=== Round {round_num}/{max_rounds} ===")
            
            # Store forum guidance for agents (Forum Reader pattern)
            self._forum_state = {
                "round": round_num,
                "guidance": forum_guidance,
                "previous_query": current_query
            }
            
            # Run parallel research
            round_result = self._deep_discuss_parallel(current_query)
            round_result["round"] = round_num
            all_reports.append(round_result)
            
            if not round_result.get("success"):
                break
            
            # Check if we should continue
            host_analysis = round_result.get("host_analysis", "")
            needs_more = self._check_needs_more_research(host_analysis)
            
            if not needs_more or round_num >= max_rounds:
                break
            
            # Extract refined query from host guidance (Step 5.3)
            refined = self._extract_refined_query(host_analysis, current_query)
            if refined and refined != current_query:
                forum_guidance = self._build_forum_guidance(host_analysis)
                current_query = refined
                logger.info(f"Refined query for next round: {refined}")
            else:
                break
        
        # Final synthesis
        final_result = all_reports[-1] if all_reports else {"success": False}
        final_result["rounds_completed"] = len(all_reports)
        final_result["all_rounds"] = all_reports
        final_result["execution_mode"] = "iterative"
        
        return final_result
    
    def _check_needs_more_research(self, host_analysis: str) -> bool:
        """Check if host suggests more research is needed."""
        indicators = [
            "需要进一步", "建议深入", "有待验证", 
            "信息不足", "需要更多", "further research",
            "存在矛盾", "需要确认"
        ]
        return any(ind in host_analysis for ind in indicators)
    
    def _extract_refined_query(self, host_analysis: str, original: str) -> str:
        """Extract refined research direction from host guidance."""
        # Look for specific guidance patterns
        patterns = [
            "建议关注:", "应该深入:", "下一步研究:",
            "focus on:", "investigate:"
        ]
        
        for pattern in patterns:
            if pattern in host_analysis:
                # Extract the suggestion after the pattern
                start = host_analysis.find(pattern) + len(pattern)
                end = host_analysis.find("\n", start)
                if end == -1:
                    end = min(start + 100, len(host_analysis))
                suggestion = host_analysis[start:end].strip()
                if suggestion:
                    return suggestion
        
        return original
    
    def _build_forum_guidance(self, host_analysis: str) -> str:
        """Build guidance summary for next round's agents."""
        return f"""【论坛主持人引导】
基于上轮讨论，以下是需要深入研究的方向：

{host_analysis[:500]}

请各Agent在本轮研究中重点关注上述问题。"""
    
    def get_forum_reader(self) -> 'ForumReader':
        """
        Get forum reader for agents to access discussion state.
        
        Implements Step 5.3: 交流融合
        Agents can use this to adjust their research direction.
        """
        return ForumReader(self)
    def run_full_analysis(
        self, 
        query: str,
        generate_pdf: bool = False,
        parallel: bool = True,
        max_rounds: int = 1,
        crawl_first: bool = False,
        platforms: List[str] = None,
        skip_report: bool = False
    ) -> Dict:
        """
        Run FULL BettaFish analysis pipeline and generate report.
        
        This is the complete workflow matching BettaFish Streamlit UI:
        1. (Optional) Crawl fresh data via MediaCrawlerPro
        2. Run all 3 engines in parallel (Insight, Media, Query)
        3. Save engine reports to BettaFish directories
        4. Run ForumEngine discussion synthesis
        5. Generate final HTML/PDF report via ReportEngine
        
        Args:
            query: Research topic (e.g., "小牛电动车品牌分析")
            generate_pdf: Whether to generate PDF (requires WeasyPrint)
            parallel: Run engines in parallel (recommended)
            max_rounds: Forum discussion rounds (1 = single pass)
            crawl_first: If True, run MediaCrawlerPro to get fresh data before analysis
            platforms: Platforms to crawl (default: ["xhs"]). Options: xhs, weibo, douyin, bilibili
            
        Returns:
            Dict with engine_reports, final_report paths, forum_synthesis
        """
        import time
        import subprocess
        from datetime import datetime
        from pathlib import Path
        
        start_time = time.time()
        logger.info(f"Starting FULL BettaFish analysis: {query}")
        
        # BettaFish report directories
        bettafish_path = Path(BETTAFISH_PATH)
        insight_dir = bettafish_path / "insight_engine_streamlit_reports"
        media_dir = bettafish_path / "media_engine_streamlit_reports"
        query_dir = bettafish_path / "query_engine_streamlit_reports"
        final_dir = bettafish_path / "final_reports"
        
        # Ensure directories exist
        for d in [insight_dir, media_dir, query_dir, final_dir]:
            d.mkdir(parents=True, exist_ok=True)
        
        crawl_results = {}
        
        # Step 0 (Optional): Crawl fresh data via MediaCrawlerPro
        if crawl_first:
            logger.info("Step 0/4: Crawling fresh data via MediaCrawlerPro...")
            crawl_platforms = platforms or ["xhs"]
            
            mediacrawler_path = Path("/home/jimmy/Documents/mcn/external/MediaCrawlerPro-Python")
            
            for platform in crawl_platforms:
                try:
                    logger.info(f"  Crawling {platform} for: {query}")
                    
                    # Prepare robust environment for headless subprocess (Gemini Deep Think fix)
                    crawl_env = os.environ.copy()
                    crawl_env.update({
                        # CRITICAL: Disables Typer/Rich pretty-printing
                        # Forces raw Python stack trace instead of crashing silently
                        "_TYPER_STANDARD_TRACEBACK": "1",
                        
                        # Forces Python to flush stdout/stderr immediately
                        "PYTHONUNBUFFERED": "1",
                        
                        # Fixes Click/Typer "RuntimeError: Aborting" on ASCII locales
                        "LC_ALL": "C.UTF-8",
                        "LANG": "C.UTF-8",
                        
                        # Ensures Playwright can find browsers
                        "HOME": os.environ.get("HOME", "/home/jimmy"),
                        
                        # Fakes terminal size to prevent Rich layout crashes
                        "FORCE_COLOR": "1",
                        "TERM": "xterm-256color",
                        "COLUMNS": "120",
                        "LINES": "24"
                    })
                    
                    cmd_list = [
                        str(mediacrawler_path / '.venv/bin/python'),
                        "main.py",
                        "--platform", platform,
                        "--type", "search",
                        "--keywords", query
                    ]
                    
                    result = subprocess.run(
                        cmd_list,
                        cwd=str(mediacrawler_path),
                        env=crawl_env,
                        capture_output=True,
                        text=True,
                        timeout=600  # 10 min per platform
                    )
                    
                    if result.returncode == 0:
                        crawl_results[platform] = {"success": True}
                        logger.info(f"  ✓ {platform} crawl complete")
                    else:
                        # Combine stdout and stderr to find the error
                        full_log = (result.stderr + result.stdout).strip()
                        
                        if not full_log:
                            full_log = "[Silent Exit 1: No Output Captured - Check Permissions]"
                        
                        logger.error(f"  ✗ {platform} crawl failed (Exit {result.returncode})")
                        logger.error(f"    Traceback: {full_log[:500]}")
                        crawl_results[platform] = {"success": False, "error": full_log[:500]}
                        
                except subprocess.TimeoutExpired:
                    crawl_results[platform] = {"success": False, "error": "Timeout (5 min)"}
                    logger.warning(f"  ✗ {platform} crawl timed out")
                except Exception as e:
                    crawl_results[platform] = {"success": False, "error": str(e)}
                    logger.error(f"  ✗ {platform} crawl error: {e}")
        
        # Step 1: Run all engines via deep_discuss
        step_label = "Step 1/3" if not crawl_first else "Step 1/4"
        logger.info(f"{step_label}: Running all engines in parallel...")
        discuss_result = self.deep_discuss(
            query=query, 
            include_all_engines=True, 
            parallel=parallel,
            max_rounds=max_rounds
        )
        
        if not discuss_result.get("success"):
            return {
                "success": False,
                "error": f"Engine analysis failed: {discuss_result.get('error')}",
                "execution_time_seconds": time.time() - start_time
            }
        
        # Step 2: Save engine reports to files
        logger.info("Step 2/3: Saving engine reports...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        query_slug = query.replace(" ", "_")[:30]
        
        engine_reports = {}
        agent_reports = discuss_result.get("agent_reports", {})
        
        # Save Insight report
        if "insight" in agent_reports:
            insight_path = insight_dir / f"deep_search_report_{query_slug}_{timestamp}.md"
            with open(insight_path, 'w', encoding='utf-8') as f:
                f.write(f"# {query} - Insight Engine分析报告\n\n")
                f.write(f"生成时间: {datetime.now().isoformat()}\n\n")
                f.write("## 私有数据库深度分析\n\n")
                f.write(agent_reports["insight"])
            engine_reports["insight"] = str(insight_path)
            logger.info(f"Saved Insight report: {insight_path}")
        
        # Save Media report
        if "media" in agent_reports:
            media_path = media_dir / f"deep_search_report_{query_slug}_{timestamp}.md"
            with open(media_path, 'w', encoding='utf-8') as f:
                f.write(f"# {query} - Media Engine分析报告\n\n")
                f.write(f"生成时间: {datetime.now().isoformat()}\n\n")
                f.write("## 多模态内容深度分析\n\n")
                f.write(agent_reports["media"])
            engine_reports["media"] = str(media_path)
            logger.info(f"Saved Media report: {media_path}")
        
        # Save Query report
        if "query" in agent_reports:
            query_path = query_dir / f"deep_search_report_{query_slug}_{timestamp}.md"
            with open(query_path, 'w', encoding='utf-8') as f:
                f.write(f"# {query} - Query Engine分析报告\n\n")
                f.write(f"生成时间: {datetime.now().isoformat()}\n\n")
                f.write("## Web广度搜索深度分析\n\n")
                f.write(agent_reports["query"])
            engine_reports["query"] = str(query_path)
            logger.info(f"Saved Query report: {query_path}")
        
        # Step 3: Generate final report via ReportEngine (optional - skip if skip_report=True)
        final_report = {}
        
        if skip_report:
            logger.info("Step 3/3: Skipping ReportEngine (skip_report=True)")
            final_report["skipped"] = True
        else:
            logger.info("Step 3/3: Generating final report...")
            try:
                # Import and run ReportEngine
                import subprocess
                
                report_cmd = [
                    str(bettafish_path / ".venv/bin/python"),
                    str(bettafish_path / "report_engine_only.py"),
                    "--query", query,
                    "--no-confirm"
                ]
                
                if not generate_pdf:
                    report_cmd.append("--skip-pdf")
                
                result = subprocess.run(
                    report_cmd,
                    capture_output=True,
                    text=True,
                    timeout=1200,  # 20 minute timeout
                    cwd=str(bettafish_path)
                )
                
                if result.returncode == 0:
                    # Find the generated report
                    html_files = sorted(
                        final_dir.glob(f"final_report_*_{timestamp[:8]}*.html"),
                        key=lambda x: x.stat().st_mtime,
                        reverse=True
                    )
                    if html_files:
                        final_report["html_path"] = str(html_files[0])
                        logger.info(f"Generated HTML report: {html_files[0]}")
                    
                    if generate_pdf:
                        pdf_files = sorted(
                            final_dir.glob(f"final_report_*_{timestamp[:8]}*.pdf"),
                            key=lambda x: x.stat().st_mtime,
                            reverse=True
                        )
                        if pdf_files:
                            final_report["pdf_path"] = str(pdf_files[0])
                else:
                    logger.warning(f"ReportEngine exited with code {result.returncode}")
                    if result.stderr:
                        logger.error(f"ReportEngine stderr: {result.stderr[:1000]}")
                    if result.stdout:
                        logger.info(f"ReportEngine stdout (last 500 chars): {result.stdout[-500:]}")
                    final_report["error"] = result.stderr[:500] if result.stderr else "Unknown error"
                    
            except subprocess.TimeoutExpired:
                logger.error("ReportEngine timed out")
                final_report["error"] = "Report generation timed out (20 min limit)"
            except Exception as e:
                logger.error(f"ReportEngine failed: {e}")
                final_report["error"] = str(e)
        
        execution_time = time.time() - start_time
        logger.info(f"Full analysis complete in {execution_time:.1f}s")
        
        return {
            "success": True,
            "query": query,
            "crawl_results": crawl_results if crawl_first else None,
            "engine_reports": engine_reports,
            "final_report": final_report,
            "forum_synthesis": discuss_result.get("host_analysis", ""),
            "conflicts_detected": discuss_result.get("conflicts_detected", 0),
            "rounds_completed": discuss_result.get("rounds_completed", 1),
            "execution_time_seconds": round(execution_time, 2)
        }




class ForumReader:
    """
    Forum Reader Tool for agents to read discussion state.
    
    Enables agents to:
    - Read host guidance from previous rounds
    - See other agents' findings
    - Adjust research direction accordingly
    """
    
    def __init__(self, forum_engine: ForumEngineWrapper):
        self._engine = forum_engine
    
    def get_current_round(self) -> int:
        """Get current discussion round number."""
        state = getattr(self._engine, '_forum_state', {})
        return state.get("round", 1)
    
    def get_host_guidance(self) -> Optional[str]:
        """
        Get host guidance from previous round.
        
        Returns:
            Host's guidance/suggestions, or None if first round
        """
        state = getattr(self._engine, '_forum_state', {})
        return state.get("guidance")
    
    def get_previous_query(self) -> Optional[str]:
        """Get the query from the previous round."""
        state = getattr(self._engine, '_forum_state', {})
        return state.get("previous_query")
    
    def should_focus_on(self) -> List[str]:
        """
        Extract focus areas from host guidance.
        
        Returns:
            List of topics/areas to focus on
        """
        guidance = self.get_host_guidance()
        if not guidance:
            return []
        
        focus_areas = []
        keywords = ["关注", "深入", "研究", "分析", "验证"]
        
        lines = guidance.split("\n")
        for line in lines:
            for kw in keywords:
                if kw in line:
                    # Extract the focus phrase
                    clean = line.strip("- •").strip()
                    if len(clean) > 5 and len(clean) < 100:
                        focus_areas.append(clean)
                    break
        
        return focus_areas[:5]  # Top 5 focus areas



# Singleton
_engine: Optional[ForumEngineWrapper] = None


def get_forum_engine() -> ForumEngineWrapper:
    """Get or create the ForumEngine wrapper singleton."""
    global _engine
    if _engine is None:
        _engine = ForumEngineWrapper()
    return _engine

