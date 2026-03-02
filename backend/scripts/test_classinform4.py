"""Check the МО page and ГО page for Altai Krai on classinform.ru"""
import requests
from bs4 import BeautifulSoup
import time

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml',
    'Accept-Language': 'ru-RU,ru;q=0.9',
}

for code, name in [("01500000000", "Муниципальные ОКРУГА"), ("01700000000", "Городские округа")]:
    url = f"https://classinform.ru/oktmo/{code}.html"
    print(f"\n=== {name} ({code}) ===")
    print(f"URL: {url}")
    resp = requests.get(url, headers=HEADERS, timeout=60)
    print(f"Status: {resp.status_code}, Length: {len(resp.text)}")
    
    soup = BeautifulSoup(resp.text, 'html.parser')
    body = soup.find('body')
    text = body.get_text('\n', strip=True) if body else ''
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    
    # Find content section
    in_content = False
    for line in lines:
        if 'округ' in line.lower() or 'ЗАТО' in line or 'город' in line.lower():
            in_content = True
        if in_content:
            print(f"  {line[:200]}")
        if 'Полная расшифровка' in line:
            break
    
    # Links
    for a in soup.find_all('a'):
        href = a.get('href', '')
        atext = a.get_text(strip=True)
        if '/oktmo/01' in href and '.html' in href and not atext[0:1].isdigit() and len(atext) > 5:
            if '000000' not in href[-15:-5]:  # not a category
                print(f"  LINK: {atext[:150]}")
    
    time.sleep(1)
