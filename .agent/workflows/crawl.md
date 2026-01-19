---
description: How to crawl social media data using MediaCrawlerPro for BettaFish analysis
---

# MediaCrawlerPro Crawl Workflow

## Prerequisites
- Sign service must be running on port 8989
- Valid account cookies in database or xlsx file
- See [MEDIACRAWLERPRO_COOKIES.md](/home/jimmy/Documents/mcn/docs/MEDIACRAWLERPRO_COOKIES.md) for cookie setup

---

## Step 1: Start Sign Service
// turbo
```bash
cd /home/jimmy/Documents/mcn/external/MediaCrawlerPro-SignSrv && source .venv/bin/activate && python app.py &
```

Wait for startup:
// turbo
```bash
sleep 3 && curl -s http://localhost:8989/signsrv/pong
```

---

## Step 2: Run Crawler

### XiaoHongShu (XHS) - Most Common
```bash
cd /home/jimmy/Documents/mcn/external/MediaCrawlerPro-Python
source .venv/bin/activate
python main.py --platform xhs --type search --keywords "YOUR_KEYWORD" --enable_checkpoint
```

### Multiple Keywords
```bash
python main.py --platform xhs --type search --keywords "关键词1,关键词2,关键词3"
```

### Other Platforms
```bash
# Douyin
python main.py --platform dy --type search --keywords "关键词"

# Weibo  
python main.py --platform wb --type search --keywords "关键词"

# Bilibili
python main.py --platform bili --type search --keywords "关键词"

# Zhihu
python main.py --platform zhihu --type search --keywords "关键词"

# Kuaishou
python main.py --platform ks --type search --keywords "关键词"

# Tieba
python main.py --platform tieba --type search --keywords "关键词"
```

---

## Step 3: Verify Data in BettaFish
// turbo
```bash
cd /home/jimmy/Documents/mcn/middleware && .venv/bin/python -c "
from lib.bettafish_client import BettaFishClient
bf = BettaFishClient()
topics = bf.search_topics('YOUR_KEYWORD', hours=168, limit=10)
print(f'Found {len(topics)} topics')
for t in topics[:5]:
    print(f'  - {t[\"title\"][:50]}...')
"
```

---

## Troubleshooting

### Cookie Expired ("账号池中没有可用的账号")

**Quick Fix:**
1. Install **Cookie-Editor** Chrome extension
2. Login to platform in browser
3. Click Cookie-Editor → Export → Copy
4. Update database:

```sql
mysql -u root -p media_crawler_pro -e "
UPDATE crawler_cookies_account 
SET cookies = 'YOUR_NEW_COOKIES_HERE',
    status = 0
WHERE platform_name = 'xhs';
"
```

**Platform-specific notes:**
- **微博**: Must use H5 page (https://m.weibo.cn)
- **知乎**: Must export from search results page

See full guide: [MEDIACRAWLERPRO_COOKIES.md](/home/jimmy/Documents/mcn/docs/MEDIACRAWLERPRO_COOKIES.md)

### Sign Service Not Running
```bash
cd /home/jimmy/Documents/mcn/external/MediaCrawlerPro-SignSrv
source .venv/bin/activate
python app.py &
```

### Rate Limited
- Increase `CRAWLER_TIME_SLEEP` in config/base_config.py
- Wait 1-2 hours before retrying

---

## Configuration

Edit `/home/jimmy/Documents/mcn/external/MediaCrawlerPro-Python/config/base_config.py`:

```python
# Posts per keyword (default: 40)
CRAWLER_MAX_NOTES_COUNT = 40

# Enable comments (default: True)
ENABLE_GET_COMMENTS = True

# Delay between requests (default: 1 second)
CRAWLER_TIME_SLEEP = 1

# Account storage: "mysql" or "xlsx"
ACCOUNT_POOL_SAVE_TYPE = "mysql"
```
