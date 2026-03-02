"""Debug: check classinform.ru format for Kaliningrad Oblast"""
import requests
from bs4 import BeautifulSoup
import time

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml',
    'Accept-Language': 'ru-RU,ru;q=0.9',
}

# Check main page for categories
for code, name in [("27000000000", "Калининград - MAIN"),
                    ("27500000000", "Калининград - МО"),
                    ("27600000000", "Калининград - МР"),
                    ("27700000000", "Калининград - ГО")]:
    url = f"https://classinform.ru/oktmo/{code}.html"
    print(f"\n=== {name} ===")
    resp = requests.get(url, headers=HEADERS, timeout=60)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        soup = BeautifulSoup(resp.text, 'html.parser')
        body = soup.find('body')
        text = body.get_text('\n', strip=True) if body else ''
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        
        in_content = False
        for line in lines:
            if '27' in line and any(c.isdigit() for c in line[:2]):
                in_content = True
            if in_content:
                print(f"  {line[:200]}")
            if 'Полная расшифровка' in line:
                break
    else:
        print(f"  Page not found (status {resp.status_code})")
    time.sleep(1)

# Also check КБР (code 83)
print("\n\n=== КБР ГО ===")
url = "https://classinform.ru/oktmo/83700000000.html"
resp = requests.get(url, headers=HEADERS, timeout=60)
if resp.status_code == 200:
    soup = BeautifulSoup(resp.text, 'html.parser')
    body = soup.find('body')
    text = body.get_text('\n', strip=True) if body else ''
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    in_content = False
    for line in lines:
        if '83' in line and any(c.isdigit() for c in line[:2]):
            in_content = True
        if in_content:
            print(f"  {line[:200]}")
        if 'Полная расшифровка' in line:
            break
