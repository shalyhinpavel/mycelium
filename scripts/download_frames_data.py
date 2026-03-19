import httpx
import json
import logging
import os
import re
from bs4 import BeautifulSoup

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

URL_FILE = "datasets/frames_wiki_urls.txt"
OUTPUT_FILE = "datasets/frames_ingestion_data.json"

async def download_urls():
    if not os.path.exists(URL_FILE):
        logger.error(f"File not found: {URL_FILE}")
        return

    with open(URL_FILE, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip().startswith("http")]

    logger.info(f"🚀 Starting download of {len(urls)} URLs...")
    results = []

    async with httpx.AsyncClient(
        timeout=20.0, 
        follow_redirects=True,
        headers={"User-Agent": "MyceliumBenchmark/1.0 (shalyhinpavel@gmail.com) Python-httpx/0.28.1"}
    ) as client:
        for i, url in enumerate(urls):
            try:
                logger.info(f"[{i+1}/{len(urls)}] Fetching: {url}")
                resp = await client.get(url)
                resp.raise_for_status()

                soup = BeautifulSoup(resp.text, "html.parser")
                
                # Extract Title
                title = soup.title.string.strip() if soup.title and soup.title.string else url
                # Remove suffix " - Wikipedia" if present
                title = re.sub(r' - Wikipedia$', '', title).strip()

                # Clean HTML - specifically for Wikipedia
                content_div = soup.find(id="mw-content-text")
                if content_div:
                    # Remove unwanted elements inside content
                    for tag in content_div(["script", "style", "nav", "table", "div.printfooter", "div.mw-editsection"]):
                        tag.decompose()
                    body_text = content_div.get_text(separator="\n", strip=True)
                else:
                    # Fallback to general cleaning
                    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                        tag.decompose()
                    body_text = soup.get_text(separator="\n", strip=True)

                if body_text:
                    results.append({
                        "id": f"wiki_{i}",
                        "title": title,
                        "content": body_text,
                        "metadata": {"url": url, "source": "wikipedia"}
                    })
                    logger.info(f"   ✅ Done: {title[:50]}...")
                else:
                    logger.warning(f"   ⚠️ No text found for {url}")
            except Exception as e:
                logger.error(f"   ❌ Failed {url}: {e}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    logger.info(f"🏁 Finished! Saved {len(results)} pages to {OUTPUT_FILE}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(download_urls())
