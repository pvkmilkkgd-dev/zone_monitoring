"""Test different OKTMO data sources"""
import requests
from bs4 import BeautifulSoup

HEADERS = {'User-Agent': 'Mozilla/5.0'}

# Source 1: okp-okpd.ru - check if base URL works
print("=== okp-okpd.ru ===")
try:
    r = requests.get("https://www.okp-okpd.ru/", timeout=10, headers=HEADERS)
    print(f"  Base: {r.status_code}")
except Exception as e:
    print(f"  Base: {e}")

try:
    r = requests.get("https://www.okp-okpd.ru/oktmo.html", timeout=10, headers=HEADERS)
    print(f"  OKTMO page: {r.status_code}")
except Exception as e:
    print(f"  OKTMO page: {e}")

# Source 2: classifikator.ru
print("\n=== classifikator.ru ===")
try:
    r = requests.get("https://classifikator.ru/klassifikatory/oktmo", timeout=10, headers=HEADERS)
    print(f"  Status: {r.status_code}, length: {len(r.text)}")
    r.encoding = 'utf-8'
    soup = BeautifulSoup(r.text, 'html.parser')
    links = [a for a in soup.find_all('a') if 'oktmo' in a.get('href', '').lower()]
    print(f"  OKTMO links: {len(links)}")
    for a in links[:5]:
        print(f"    {a.get('href','')} -> {a.get_text(strip=True)[:60]}")
except Exception as e:
    print(f"  Error: {e}")

# Source 3: gks.ru (Rosstat)
print("\n=== rosstat ===")
try:
    r = requests.get("https://rosstat.gov.ru/opendata/7708234640-oktmo", timeout=10, headers=HEADERS)
    print(f"  Status: {r.status_code}")
except Exception as e:
    print(f"  Error: {e}")

# Source 4: Try to find OKTMO on Wikipedia-style sources  
print("\n=== Try simple Google-like approach ===")
# Actually, let me just check if the existing OKTМО scraping code in the repo works
import sys, os
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

# Check what scripts exist for OKTМО
import glob
scripts = glob.glob(r'c:\Users\Lucky\Documents\zone_monitoring\backend\scripts\*oktmo*')
scripts += glob.glob(r'c:\Users\Lucky\Documents\zone_monitoring\backend\scripts\*OKTMO*')
scripts += glob.glob(r'c:\Users\Lucky\Documents\zone_monitoring\backend\scripts\*name*')
for s in scripts:
    print(f"  Found: {os.path.basename(s)}")
