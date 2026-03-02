"""Get full list of Moscow districts from ОКТМО (453, 458 - внутригородские территории)."""
import sys, time, re, requests
from bs4 import BeautifulSoup

BASE = "https://classinform.ru"
HEADERS = {'User-Agent': 'Mozilla/5.0', 'Accept': 'text/html', 'Accept-Language': 'ru-RU,ru;q=0.9'}

def fetch_entries(prefix):
    url = f"{BASE}/oktmo/{prefix}00000000.html"
    time.sleep(1)
    resp = requests.get(url, headers=HEADERS, timeout=60)
    if resp.status_code != 200:
        return []
    soup = BeautifulSoup(resp.text, 'html.parser')
    lines = [l.strip() for l in soup.get_text('\n', strip=True).split('\n') if l.strip()]
    entries = []
    i = 0
    while i < len(lines):
        if re.match(r'^45[0-9]{6}$', lines[i]) and lines[i][3:6] != '000':
            code = lines[i]
            if i + 1 < len(lines):
                name = re.sub(r'\s*\([^)]*\)\s*$', '', lines[i+1]).strip()
                if name and not name.startswith('Код'):
                    entries.append((code, name))
        i += 1
    return entries

# 453 - внутригородские территории (муниципальные округа в старой Москве)
# 458 - внутригородские территории (Новая Москва - поселения и т.д.)
all_entries = []
for prefix in ['453', '454', '455', '456', '457', '458']:
    entries = fetch_entries(prefix)
    print(f"{prefix}: {len(entries)} entries")
    all_entries.extend(entries)

# Dedupe by code
by_code = {c: n for c, n in all_entries}
print(f"\nВсего уникальных по коду: {len(by_code)}")
for code in sorted(by_code.keys())[:80]:
    print(f"  {code} {by_code[code]}")
if len(by_code) > 80:
    print(f"  ... и ещё {len(by_code) - 80}")
