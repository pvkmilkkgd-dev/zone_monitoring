"""Debug: see raw page structure for classinform.ru ОКТМО subcategory"""
import requests
from bs4 import BeautifulSoup
import time

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml',
    'Accept-Language': 'ru-RU,ru;q=0.9',
}

url = "https://classinform.ru/oktmo/01600000000.html"
print(f"Fetching {url}...")
resp = requests.get(url, headers=HEADERS, timeout=60)
print(f"Status: {resp.status_code}, Length: {len(resp.text)}")

soup = BeautifulSoup(resp.text, 'html.parser')
body = soup.find('body')
text = body.get_text('\n', strip=True) if body else resp.text
lines = [l.strip() for l in text.split('\n') if l.strip()]

# Print meaningful lines (skip nav/footer)
in_content = False
for line in lines:
    if 'Муниципальные район' in line:
        in_content = True
    if in_content:
        print(line[:200])
    if 'Полная расшифровка' in line:
        break

print("\n--- All links on page ---")
for a in soup.find_all('a'):
    href = a.get('href', '')
    text = a.get_text(strip=True)
    if '/oktmo/' in href and '01' in href:
        print(f"  {href} -> {text[:100]}")
