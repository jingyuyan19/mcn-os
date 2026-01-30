#!/usr/bin/env python3
"""
3-way scraper comparison: Crawl4AI vs Jina vs Firecrawl
"""
import asyncio
import sys
import os
import time
import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "middleware"))
from middleware.lib.mirothinker_client import MiroThinkerClient

# Firecrawl API key (provided by user)
FIRECRAWL_API_KEY = "fc-44855b4153454f5eb832bb4f6befb1c0"


async def scrape_with_firecrawl(url: str) -> dict:
    """Scrape URL using Firecrawl API."""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.firecrawl.dev/v1/scrape",
                headers={
                    "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "url": url,
                    "formats": ["markdown"],
                    "includeTags": ["article", "main", ".content", "#content"]  # Focus on main content
                }
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("success"):
                markdown = data.get("data", {}).get("markdown", "")
                return {
                    "success": True,
                    "content": markdown,
                    "char_count": len(markdown),
                    "title": data.get("data", {}).get("metadata", {}).get("title", ""),
                    "error": ""
                }
            else:
                return {
                    "success": False,
                    "content": "",
                    "char_count": 0,
                    "error": data.get("error", "Unknown error")
                }
    except Exception as e:
        return {
            "success": False,
            "content": "",
            "char_count": 0,
            "error": str(e)
        }


async def compare_scrapers(url: str):
    """Compare all three scrapers on the same URL."""
    print(f"\n🔬 3-Way Scraper Comparison: {url}\n")
    print("=" * 80)
    
    client = MiroThinkerClient()
    results = {}
    
    # Test Crawl4AI (Docker)
    print("\n📦 Crawl4AI (Docker):")
    print("-" * 40)
    start = time.time()
    result = await client.scrape_url(url)
    crawl_time = time.time() - start
    results["crawl4ai"] = {**result, "time": crawl_time}
    
    if result["success"]:
        print(f"  ✅ {result.get('char_count', 0):,} chars in {crawl_time:.2f}s")
        print(f"  📝 Preview: {result['content'][:200].replace(chr(10), ' ')}...")
    else:
        print(f"  ❌ Failed: {result['error']}")
    
    # Test Jina
    print("\n🔮 Jina Reader:")
    print("-" * 40)
    start = time.time()
    result = await client.scrape_url_jina(url)
    jina_time = time.time() - start
    results["jina"] = {**result, "time": jina_time}
    
    if result["success"]:
        print(f"  ✅ {result.get('char_count', 0):,} chars in {jina_time:.2f}s")
        print(f"  📝 Preview: {result['content'][:200].replace(chr(10), ' ')}...")
    else:
        print(f"  ❌ Failed: {result['error']}")
    
    # Test Firecrawl
    print("\n🔥 Firecrawl:")
    print("-" * 40)
    start = time.time()
    result = await scrape_with_firecrawl(url)
    fire_time = time.time() - start
    results["firecrawl"] = {**result, "time": fire_time}
    
    if result["success"]:
        print(f"  ✅ {result.get('char_count', 0):,} chars in {fire_time:.2f}s")
        print(f"  📝 Preview: {result['content'][:200].replace(chr(10), ' ')}...")
    else:
        print(f"  ❌ Failed: {result['error']}")
    
    # Summary table
    print("\n" + "=" * 80)
    print("📊 COMPARISON SUMMARY")
    print("=" * 80)
    print(f"{'Metric':<20} {'Crawl4AI':>15} {'Jina':>15} {'Firecrawl':>15} {'Winner':>15}")
    print("-" * 80)
    
    # Characters
    chars = {
        "crawl4ai": results["crawl4ai"].get("char_count", 0),
        "jina": results["jina"].get("char_count", 0),
        "firecrawl": results["firecrawl"].get("char_count", 0)
    }
    winner = max(chars, key=chars.get) if any(chars.values()) else "N/A"
    print(f"{'Characters':<20} {chars['crawl4ai']:>15,} {chars['jina']:>15,} {chars['firecrawl']:>15,} {winner.title():>15}")
    
    # Time
    times = {
        "crawl4ai": results["crawl4ai"].get("time", 99),
        "jina": results["jina"].get("time", 99),
        "firecrawl": results["firecrawl"].get("time", 99)
    }
    winner = min(times, key=times.get)
    print(f"{'Time (seconds)':<20} {times['crawl4ai']:>15.2f} {times['jina']:>15.2f} {times['firecrawl']:>15.2f} {winner.title():>15}")
    
    # Quality assessment
    print("\n📋 CONTENT QUALITY NOTES:")
    
    crawl_content = results["crawl4ai"].get("content", "")
    jina_content = results["jina"].get("content", "")
    fire_content = results["firecrawl"].get("content", "")
    
    # Check for navigation pollution
    nav_keywords = ["log in", "sign up", "menu", "cookie", "skip to", "switch to"]
    
    crawl_has_nav = any(kw in crawl_content.lower()[:500] for kw in nav_keywords)
    jina_has_nav = any(kw in jina_content.lower()[:500] for kw in nav_keywords)
    fire_has_nav = any(kw in fire_content.lower()[:500] for kw in nav_keywords)
    
    print(f"  - Crawl4AI: {'⚠️  Has navigation/menu content' if crawl_has_nav else '✅ Clean article content'}")
    print(f"  - Jina:     {'⚠️  Has navigation/menu content' if jina_has_nav else '✅ Clean article content'}")
    print(f"  - Firecrawl: {'⚠️  Has navigation/menu content' if fire_has_nav else '✅ Clean article content'}")
    
    return results


async def main():
    test_urls = [
        "https://openai.com/index/introducing-chatgpt-health/",
    ]
    
    if len(sys.argv) > 1:
        test_urls = [sys.argv[1]]
    
    for url in test_urls:
        await compare_scrapers(url)


if __name__ == "__main__":
    asyncio.run(main())
