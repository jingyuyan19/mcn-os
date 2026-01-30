#!/usr/bin/env python3
"""
Test script for MiroThinker Deep Research integration.
Tests the scraping and research pipeline.
"""
import asyncio
import sys
import os

# Add middleware to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "middleware"))

from middleware.lib.mirothinker_client import MiroThinkerClient


async def test_scrape():
    """Test URL scraping with Crawl4AI."""
    print("=" * 60)
    print("TEST 1: Crawl4AI Scraping")
    print("=" * 60)
    
    client = MiroThinkerClient()
    url = "https://techcrunch.com/category/artificial-intelligence/"
    
    print(f"Scraping: {url}")
    result = await client.scrape_url(url)
    
    if result["success"]:
        print(f"✅ Success! Scraped {result.get('char_count', 0)} characters")
        print(f"   Title: {result.get('title', 'N/A')}")
        print(f"   Preview: {result['content'][:200]}...")
    else:
        print(f"❌ Failed: {result['error']}")
    
    return result["success"]


async def test_web_search():
    """Test Serper web search."""
    print("\n" + "=" * 60)
    print("TEST 2: Serper Web Search")
    print("=" * 60)
    
    client = MiroThinkerClient()
    
    if not client.serper_api_key:
        print("⚠️  Serper API key not configured, skipping search test")
        return True
    
    query = "AI news today"
    print(f"Searching: {query}")
    
    results = await client.web_search(query, num_results=3)
    
    if results:
        print(f"✅ Found {len(results)} results:")
        for r in results[:3]:
            print(f"   - {r.get('title', 'N/A')}")
    else:
        print("❌ No results found")
    
    return len(results) > 0


async def test_research_flow():
    """Test full research and screenwriting flow."""
    print("\n" + "=" * 60)
    print("TEST 3: Full Research Flow (Scrape + MiroThinker)")
    print("=" * 60)
    
    client = MiroThinkerClient()
    
    if not client.is_available():
        print("⚠️  MiroThinker model not available in Ollama, skipping")
        return True
    
    url = "https://techcrunch.com/category/artificial-intelligence/"
    
    print(f"Running deep research on: {url}")
    print("This may take 1-3 minutes...")
    
    result = await client.research_and_screenwrite(
        source_url=url,
        artist_style="Tech-savvy young presenter",
        enable_scraping=True,
        enable_search=False  # Skip search for faster test
    )
    
    print(f"\n📊 Results:")
    print(f"   Scraped chars: {result.get('scraped_chars', 0)}")
    print(f"   Scrape error: {result.get('scrape_error', 'None')}")
    
    if result.get("storyboard"):
        print(f"   ✅ Storyboard generated with {len(result['storyboard'].get('scenes', []))} scenes")
        print(f"   Title: {result['storyboard'].get('title', 'N/A')}")
    else:
        print("   ⚠️  No structured storyboard extracted")
        print(f"   Raw response preview: {result.get('cleaned_response', '')[:200]}...")
    
    return True


async def main():
    print("\n🧪 MiroThinker Deep Research Test Suite\n")
    
    tests = [
        ("Crawl4AI Scraping", test_scrape),
        ("Serper Web Search", test_web_search),
    ]
    
    results = []
    for name, test_fn in tests:
        try:
            passed = await test_fn()
            results.append((name, passed))
        except Exception as e:
            print(f"❌ {name} failed with exception: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {name}")
    
    # Optional: Run full flow test
    if "--full" in sys.argv:
        print("\n🚀 Running full research flow test...")
        await test_research_flow()


if __name__ == "__main__":
    asyncio.run(main())
