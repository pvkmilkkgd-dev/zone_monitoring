import requests
from bs4 import BeautifulSoup

url = "https://okp-okpd.ru/oktmo.aspx?kod=03"
resp = requests.get(url, timeout=30)

print(f"Status: {resp.status_code}")
print(f"Encoding detected: {resp.encoding}")
print(f"Apparent encoding: {resp.apparent_encoding}")

# Try with detected encoding
soup = BeautifulSoup(resp.text, 'html.parser')
names = []
for tr in soup.find_all('tr'):
    cells = tr.find_all('td')
    if len(cells) >= 2:
        code_text = cells[0].get_text(strip=True)
        name_text = cells[1].get_text(strip=True)
        import re
        if re.match(r'^\d{11}$', code_text):
            names.append(name_text)

print(f"\nWith encoding '{resp.encoding}': {len(names)} entries")
for n in names[:5]:
    print(f"  {repr(n)}")

# Try with utf-8
resp2 = requests.get(url, timeout=30)
resp2.encoding = 'utf-8'
soup2 = BeautifulSoup(resp2.text, 'html.parser')
names2 = []
for tr in soup2.find_all('tr'):
    cells = tr.find_all('td')
    if len(cells) >= 2:
        code_text = cells[0].get_text(strip=True)
        name_text = cells[1].get_text(strip=True)
        if re.match(r'^\d{11}$', code_text):
            names2.append(name_text)

print(f"\nWith encoding 'utf-8': {len(names2)} entries")
for n in names2[:5]:
    print(f"  {repr(n)}")

# Try with windows-1251
resp3 = requests.get(url, timeout=30)
resp3.encoding = 'windows-1251'
soup3 = BeautifulSoup(resp3.text, 'html.parser')
names3 = []
for tr in soup3.find_all('tr'):
    cells = tr.find_all('td')
    if len(cells) >= 2:
        code_text = cells[0].get_text(strip=True)
        name_text = cells[1].get_text(strip=True)
        if re.match(r'^\d{11}$', code_text):
            names3.append(name_text)

print(f"\nWith encoding 'windows-1251': {len(names3)} entries")
for n in names3[:5]:
    print(f"  {repr(n)}")
