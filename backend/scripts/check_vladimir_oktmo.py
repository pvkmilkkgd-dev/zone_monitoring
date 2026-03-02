import requests, time, re
from bs4 import BeautifulSoup

BASE = "https://classinform.ru"
HEADERS = {'User-Agent': 'Mozilla/5.0', 'Accept': 'text/html', 'Accept-Language': 'ru-RU,ru;q=0.9'}

for code, label in [("17500000000", "МО"), ("17600000000", "МР"), ("17700000000", "ГО")]:
    url = f"{BASE}/oktmo/{code}.html"
    resp = requests.get(url, headers=HEADERS, timeout=60)
    if resp.status_code == 200:
        soup = BeautifulSoup(resp.text, 'html.parser')
        text = soup.find('body').get_text('\n', strip=True)
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        
        print(f"\n=== {label} ({code}) ===")
        in_content = False
        for line in lines:
            if re.match(r'^\d{8}$', line) and line.startswith('17'):
                in_content = True
            if in_content:
                print(f"  {line}")
            if 'Полная расшифровка' in line:
                break
    time.sleep(1)
