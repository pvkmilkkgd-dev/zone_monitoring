"""Test fetching OKTMO data from classinform.ru (актуальный ОКТМО с изменениями 2026)"""
import requests
from bs4 import BeautifulSoup
import time

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
}

# Test with Altai Krai (code 01)
url = "https://classinform.ru/oktmo/01000000000.html"
print(f"Fetching {url}...")
resp = requests.get(url, headers=HEADERS, timeout=60)
print(f"Status: {resp.status_code}")
print(f"Content length: {len(resp.text)}")

if resp.status_code == 200:
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    # Find all links that look like ОКТМО entries
    entries = []
    for a in soup.find_all('a'):
        href = a.get('href', '')
        text = a.get_text(strip=True)
        if '/oktmo/01' in href and len(href) > 30:
            # 8-digit codes = municipal formations
            entries.append((href, text))
    
    print(f"\nFound {len(entries)} entries:")
    for href, text in entries[:30]:
        print(f"  {href} -> {text}")
    
    if len(entries) > 30:
        print(f"  ... and {len(entries) - 30} more")
    
    # Also check raw structure
    print("\n\n--- Sample HTML structure (first table or list) ---")
    table = soup.find('table')
    if table:
        rows = table.find_all('tr')[:5]
        for r in rows:
            print(r.get_text(strip=True)[:200])
    else:
        # Check for divs with content
        content = soup.find('div', class_='content') or soup.find('main') or soup.find('body')
        if content:
            all_text = content.get_text('\n', strip=True)
            lines = [l for l in all_text.split('\n') if l.strip()]
            for l in lines[:50]:
                print(l[:200])
