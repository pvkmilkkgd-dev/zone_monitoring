"""Debug OKTMO site scraping"""
import requests
from bs4 import BeautifulSoup

url = "https://www.okp-okpd.ru/oktmo.html"
params = {'search': 'Архангельская область'}
resp = requests.get(url, params=params, timeout=30)
resp.encoding = 'windows-1251'
soup = BeautifulSoup(resp.text, 'html.parser')

print(f"Status: {resp.status_code}")
print(f"URL: {resp.url}")
print(f"\nAll links with 'oktmo':")
for a in soup.find_all('a'):
    href = a.get('href', '')
    if 'oktmo' in href.lower():
        text = a.get_text(strip=True)[:80]
        print(f"  {href} -> {text}")

# Try direct region page
print("\n\n=== Try direct region page ===")
# Region codes for Arkhangelsk: 11
url2 = "https://www.okp-okpd.ru/oktmo/11.html"
resp2 = requests.get(url2, timeout=30)
resp2.encoding = 'windows-1251'
soup2 = BeautifulSoup(resp2.text, 'html.parser')
print(f"Status: {resp2.status_code}")

for a in soup2.find_all('a'):
    href = a.get('href', '')
    if 'oktmo' in href.lower():
        text = a.get_text(strip=True)[:80]
        print(f"  {href} -> {text}")
