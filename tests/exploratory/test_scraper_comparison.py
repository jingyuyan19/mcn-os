#!/usr/bin/env python3
"""
Compare Crawl4AI vs Jina Reader scraping quality.
"""
import asyncio
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "middleware"))
from middleware.lib.mirothinker_client import MiroThinkerClient


async def compare_scrapers(url: str):
    """Compare Crawl4AI and Jina on the same URL."""
    print(f"\n🔬 Comparing scrapers on: {url}\n")
    print("=" * 70)
    
    client = MiroThinkerClient()
    
    # Test Crawl4AI
    print("\n📦 Crawl4AI:")
    print("-" * 40)
    start = time.time()
    crawl_result = await client.scrape_url(url)
    crawl_time = time.time() - start
    
    if crawl_result["success"]:
        print(f"  ✅ Success in {crawl_time:.2f}s")
        print(f"  📊 Characters: {crawl_result.get('char_count', 0):,}")
        print(f"  📝 Preview ({min(300, len(crawl_result['content']))} chars):")
        preview = crawl_result["content"][:300].replace("\n", " ")[:200]
        print(f"     {preview}...")
    else:
        print(f"  ❌ Failed: {crawl_result['error']}")
        crawl_result["content"] = ""
    
    # Test Jina
    print("\n🔮 Jina Reader:")
    print("-" * 40)
    
    if not client.jina_api_key:
        print("  ⚠️  Jina API key not configured")
        jina_result = {"success": False, "content": "", "char_count": 0}
        jina_time = 0
    else:
        start = time.time()
        jina_result = await client.scrape_url_jina(url)
        jina_time = time.time() - start
        
        if jina_result["success"]:
            print(f"  ✅ Success in {jina_time:.2f}s")
            print(f"  📊 Characters: {jina_result.get('char_count', 0):,}")
            print(f"  📝 Preview ({min(300, len(jina_result['content']))} chars):")
            preview = jina_result["content"][:300].replace("\n", " ")[:200]
            print(f"     {preview}...")
        else:
            print(f"  ❌ Failed: {jina_result['error']}")
            jina_result["content"] = ""
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 COMPARISON SUMMARY")
    print("=" * 70)
    print(f"{'Metric':<20} {'Crawl4AI':>15} {'Jina':>15} {'Winner':>15}")
    print("-" * 70)
    
    crawl_chars = crawl_result.get("char_count", 0)
    jina_chars = jina_result.get("char_count", 0)
    
    # Characters
    winner_chars = "Crawl4AI" if crawl_chars > jina_chars else "Jina" if jina_chars > crawl_chars else "Tie"
    print(f"{'Characters':<20} {crawl_chars:>15,} {jina_chars:>15,} {winner_chars:>15}")
    
    # Time
    winner_time = "Crawl4AI" if crawl_time < jina_time else "Jina" if jina_time < crawl_time else "Tie"
    print(f"{'Time (seconds)':<20} {crawl_time:>15.2f} {jina_time:>15.2f} {winner_time:>15}")
    
    # Format quality (Jina returns clean markdown, Crawl4AI returns HTML)
    crawl_is_html = crawl_result["content"].startswith("<") if crawl_result["content"] else False
    jina_is_markdown = jina_result["content"].startswith("#") or jina_result["content"].startswith("Title:") if jina_result["content"] else False
    
    crawl_format = "HTML" if crawl_is_html else "Text/MD"
    jina_format = "Markdown" if jina_is_markdown else "Text"
    print(f"{'Format':<20} {crawl_format:>15} {jina_format:>15} {'Jina*':>15}")
    
    print("\n* Jina returns clean markdown, better for LLM processing")
    
    return crawl_result, jina_result


async def main():
    # Default test URLs
    test_urls = [
        "https://example.com",  # Simple test
        "https://techcrunch.com/category/artificial-intelligence/",  # Complex site
    ]
    
    if len(sys.argv) > 1:
        test_urls = [sys.argv[1]]
    
    for url in test_urls:
        await compare_scrapers(url)
        print("\n")


if __name__ == "__main__":
    asyncio.run(main())
