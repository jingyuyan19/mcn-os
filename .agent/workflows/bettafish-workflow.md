---
description: How to run the complete BettaFish workflow for fresh topic analysis
---

# BettaFish Complete Workflow

## Overview

BettaFish is a multi-agent sentiment analysis system with the following components:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          USER ENTERS TOPIC                               │
│                      (e.g., "小牛电动车品牌分析")                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  1. MindSpider (Crawling Layer)                                          │
│     ├── BroadTopicExtraction → Extracts keywords from hot news           │
│     └── DeepSentimentCrawling → Calls MediaCrawlerPro                    │
│           └── MediaCrawlerPro-Python → Crawls XHS/Weibo/Douyin/etc.      │
│                 └── MediaCrawlerPro-SignSrv → Signs API requests         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  2. MySQL Database (media_crawler_pro)                                   │
│     Tables: xhs_note, weibo_note, bilibili_video, douyin_aweme,          │
│             zhihu_content, tieba_note, kuaishou_video + comments         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  3. Three Analysis Engines (Parallel Execution)                          │
│     ├── InsightEngine (port 8501) → Analyzes DB data with SQL queries   │
│     ├── MediaEngine (port 8502)   → Bocha AI multimodal search          │
│     └── QueryEngine (port 8503)   → Tavily web/news search              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  4. ForumEngine (Multi-Agent Discussion)                                 │
│     ├── Monitors insight.log, media.log, query.log files                │
│     ├── Detects SummaryNode outputs (FirstSummaryNode, ReflectionNode)  │
│     ├── LLM Host synthesizes discussion from 3 agents                   │
│     └── Writes discussion to forum.log                                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  5. ReportEngine (Report Generation)                                     │
│     ├── Template selection based on query type                          │
│     ├── Chapter generation with charts and tables                       │
│     └── HTML/PDF/Markdown export                                        │
└─────────────────────────────────────────────────────────────────────────┘
```

## Prerequisites

### 1. Start SignSrv (Required for crawling)
```bash
cd /home/jimmy/Documents/mcn/external/MediaCrawlerPro-SignSrv
nohup .venv/bin/python app.py > /tmp/signsrv.log 2>&1 &

# Verify it's running
curl http://localhost:8989/signsrv/pong
```

### 2. Ensure valid cookies in database
```sql
-- Check account status
SELECT id, account_name, platform_name, status FROM media_crawler_pro.crawler_cookies_account;
```

## Running Complete Workflow

### Option A: Via BettaFish Streamlit Frontend (Production)
```bash
cd /home/jimmy/Documents/mcn/external/BettaFish
.venv/bin/python app.py
# Open http://localhost:5050
# Enter topic in search box → Wait ~30 minutes for complete analysis
```

### Option B: Via CLI Components (Testing)

#### Step 1: Crawl Fresh Data
```bash
cd /home/jimmy/Documents/mcn/external/MediaCrawlerPro-Python
.venv/bin/python main.py --platform xhs --type search --keywords "小牛电动车"
```

#### Step 2: Run MindSpider (includes crawling)
```bash
cd /home/jimmy/Documents/mcn/external/BettaFish/MindSpider
python main.py --complete --test
```

#### Step 3: Run Individual Engines
```bash
cd /home/jimmy/Documents/mcn/external/BettaFish

# Run each engine separately
.venv/bin/python -m streamlit run SingleEngineApp/insight_engine_streamlit_app.py
.venv/bin/python -m streamlit run SingleEngineApp/media_engine_streamlit_app.py
.venv/bin/python -m streamlit run SingleEngineApp/query_engine_streamlit_app.py
```

#### Step 4: Generate Report
```bash
cd /home/jimmy/Documents/mcn/external/BettaFish
echo "y" | .venv/bin/python report_engine_only.py --query "小牛电动车品牌分析" --skip-pdf
```

## Key Integrations

### MindSpider → MediaCrawlerPro
Location: `/home/jimmy/Documents/mcn/external/BettaFish/MindSpider/DeepSentimentCrawling/platform_crawler.py`
```python
# Line 33 - MindSpider uses our MediaCrawlerPro installation
self.mediacrawler_path = Path("/home/jimmy/Documents/mcn/external/MediaCrawlerPro-Python")
```

### InsightEngine → MySQL
Location: `/home/jimmy/Documents/mcn/external/BettaFish/InsightEngine/tools/search.py`
- `search_topic_globally()` - Searches all platform tables
- `search_topic_by_date()` - Date-filtered search
- `search_topic_on_platform()` - Platform-specific search

### ForumEngine → Log Monitoring
Location: `/home/jimmy/Documents/mcn/external/BettaFish/ForumEngine/monitor.py`
- Monitors: `logs/insight.log`, `logs/media.log`, `logs/query.log`
- Writes: `logs/forum.log`
- Triggers host speech every 5 agent outputs

## Configuration Files

| Component | Config Location |
|-----------|-----------------|
| BettaFish | `/external/BettaFish/.env` |
| MediaCrawlerPro | `/external/MediaCrawlerPro-Python/config/db_config.py` |
| SignSrv | `/external/MediaCrawlerPro-SignSrv/config.py` |
| MindSpider | `/external/BettaFish/MindSpider/config.py` |

## Troubleshooting

### "请求签名服务器失败"
SignSrv is not running. Start it:
```bash
cd /home/jimmy/Documents/mcn/external/MediaCrawlerPro-SignSrv
nohup .venv/bin/python app.py > /tmp/signsrv.log 2>&1 &
```

### "账号池中没有可用的账号"
Cookies expired. Update in database:
```bash
# See /home/jimmy/Documents/mcn/docs/MEDIACRAWLERPRO_COOKIES.md
```

### "No data found"
Run MindSpider first to crawl data, or check if the topic exists in database.
