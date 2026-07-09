import argparse
import urllib.request
import json
import os
import re
from html import unescape

def fetch_page(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as response:
        return response.read().decode('utf-8', errors='replace')

def extract_title(html):
    match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
    return match.group(1) if match else ""

def clean_text(html):
    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.IGNORECASE)
    text = unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:3000]

def ingest_data(url, token):
    html = fetch_page(url)
    title = extract_title(html)
    text = clean_text(html)
    data = {
        "tool": "event_ingest",
        "agent_id": "browser",
        "params": {
            "source": "browser",
            "type": "page_visit",
            "content": {"url": url, "title": title, "text": text, "cookies": []},
            "ttl_days": 30
        }
    }
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    req = urllib.request.Request('http://localhost:8000/v1/ingest', json.dumps(data).encode(), headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            return response.read().decode()
    except Exception as e:
        return str(e)

def main():
    parser = argparse.ArgumentParser(description="A browsing agent that visits URLs and ingests pages.")
    parser.add_argument('--urls', nargs='+', default=["http://127.0.0.1:8901/poison"], help="URLs to visit")
    args = parser.parse_args()

    token = ""
    try:
        with open('d:/kasa/kasa.toml', 'r') as file:
            for line in file:
                match = re.search(r'bearer_token\s*=\s*"([^"]+)"', line)
                if match:
                    token = match.group(1)
                    break
    except Exception as e:
        print(f"[AGENT][ERR] Failed to read token: {e}")
        return

    ingested_count = 0
    for url in args.urls:
        try:
            response = ingest_data(url, token)
            print(f"[AGENT] visited {url} | title='{extract_title(fetch_page(url))}' | text_len={len(clean_text(fetch_page(url)))} | ingest -> {response}")
            ingested_count += 1
        except Exception as e:
            print(f"[AGENT][ERR] {url}: {e}")

    print(f"[AGENT] done: {ingested_count} pages ingested")

if __name__ == "__main__":
    main()
