"""Test fetching detailed OKTMO for Altai Krai from classinform.ru"""
import requests
from bs4 import BeautifulSoup
import time, re

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml',
    'Accept-Language': 'ru-RU,ru;q=0.9',
}

BASE = "https://classinform.ru"

def fetch_page(url):
    time.sleep(1)
    resp = requests.get(url, headers=HEADERS, timeout=60)
    return BeautifulSoup(resp.text, 'html.parser')

def extract_entries(soup, prefix):
    """Extract ОКТМО entries from a page."""
    entries = []
    for a in soup.find_all('a'):
        href = a.get('href', '')
        text = a.get_text(strip=True)
        # Match links like /oktmo/01XXXXXXX.html with 8-digit codes
        if f'/oktmo/{prefix}' in href and '.html' in href:
            # Extract the code from href
            m = re.search(r'/oktmo/(\d+)\.html', href)
            if m:
                code = m.group(1)
                if len(code) == 11 and text and not text.startswith(code[:2]):
                    entries.append((code, text))
                elif len(code) == 11 and text.isdigit():
                    pass  # skip code-only entries
    return entries

# Fetch 3 categories for Altai Krai
categories = [
    ("https://classinform.ru/oktmo/01500000000.html", "Муниципальные округа"),
    ("https://classinform.ru/oktmo/01600000000.html", "Муниципальные районы"),
    ("https://classinform.ru/oktmo/01700000000.html", "Городские округа"),
]

all_entries = []
for url, cat_name in categories:
    print(f"\n=== {cat_name} ===")
    print(f"URL: {url}")
    soup = fetch_page(url)
    
    # Get all text content
    body = soup.find('body')
    text = body.get_text('\n', strip=True) if body else ''
    
    # Find patterns like "XXXXXXXX Name" or linked entries
    for a in soup.find_all('a'):
        href = a.get('href', '')
        atext = a.get_text(strip=True)
        if '/oktmo/01' in href and '.html' in href and atext:
            m = re.search(r'/oktmo/(\d{11})\.html', href)
            if m:
                code = m.group(1)
                # Skip the category itself
                if code.endswith('000000') or code.endswith('00000'):
                    continue
                if not atext[0].isdigit():
                    print(f"  {code} -> {atext}")
                    all_entries.append((code, atext, cat_name))

print(f"\n\nTotal entries: {len(all_entries)}")
