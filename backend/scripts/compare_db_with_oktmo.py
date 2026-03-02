"""
Сравнение названий районов в БД с официальным ОКТМО (okp-okpd.ru).
Только отчёт, без изменений в БД.
Официальные названия берутся из ОКТМО как есть (без преобразования «город X» -> «городской округ X»).
"""
import os
import re
import sys
import time
import requests
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/zone_monitoring")
if db_url.startswith("postgresql+psycopg"):
    db_url = db_url.replace("postgresql+psycopg", "postgresql", 1)

from sqlalchemy import create_engine, text

ENGINE = create_engine(db_url)

# ОКТМО код -> название региона в БД (как в fix_all_names_oktmo)
OKTMO_TO_REGION = {
    "01": "Алтайский край", "03": "Краснодарский край", "04": "Красноярский край",
    "05": "Приморский край", "07": "Ставропольский край", "08": "Хабаровский край",
    "10": "Амурская область", "11": "Архангельская область", "12": "Астраханская область",
    "14": "Белгородская область", "15": "Брянская область", "17": "Владимирская область",
    "18": "Волгоградская область", "19": "Вологодская область", "20": "Воронежская область",
    "22": "Нижегородская область", "24": "Ивановская область", "25": "Иркутская область",
    "26": "Республика Ингушетия", "27": "Калининградская область", "28": "Тверская область",
    "29": "Калужская область", "30": "Камчатский край", "32": "Кемеровская область",
    "33": "Кировская область", "34": "Костромская область", "35": "Республика Крым",
    "36": "Самарская область", "37": "Курганская область", "38": "Курская область",
    "40": "город Санкт-Петербург", "41": "Ленинградская область", "42": "Липецкая область",
    "44": "Магаданская область", "45": "город Москва", "46": "Московская область",
    "47": "Мурманская область", "49": "Новгородская область", "50": "Новосибирская область",
    "52": "Омская область", "53": "Оренбургская область", "54": "Орловская область",
    "56": "Пензенская область", "57": "Пермский край", "58": "Псковская область",
    "60": "Ростовская область", "61": "Рязанская область", "63": "Саратовская область",
    "64": "Сахалинская область", "65": "Свердловская область", "66": "Смоленская область",
    "67": "город Севастополь", "68": "Тамбовская область", "69": "Томская область",
    "70": "Тульская область", "71": "Тюменская область", "73": "Ульяновская область",
    "75": "Челябинская область", "76": "Забайкальский край", "77": "Чукотский автономный округ",
    "78": "Ярославская область", "79": "Республика Адыгея", "80": "Республика Башкортостан",
    "81": "Республика Бурятия", "82": "Республика Дагестан", "83": "Кабардино-Балкарская Республика",
    "84": "Республика Алтай", "85": "Республика Калмыкия", "86": "Республика Карелия",
    "87": "Республика Коми", "88": "Республика Марий Эл", "89": "Республика Мордовия",
    "90": "Республика Северная Осетия - Алания", "91": "Карачаево-Черкесская Республика",
    "92": "Республика Татарстан", "93": "Республика Тыва", "94": "Удмуртская Республика",
    "95": "Республика Хакасия", "96": "Чеченская Республика", "97": "Чувашская Республика",
    "98": "Республика Саха (Якутия)", "99": "Еврейская автономная область",
}
AUTONOMOUS_OKRUGS = {
    "Ненецкий автономный округ": {"parent_code": "11", "prefix": "118"},
    "Ханты-Мансийский автономный округ - Югра": {"parent_code": "71", "prefix": "711"},
    "Ямало-Ненецкий автономный округ": {"parent_code": "71", "prefix": "7114"},
}

# Регионы без ОКТМО или пропускаем
SKIP = {"Донецкая Народная Республика", "Луганская Народная Республика", "Запорожская область", "Херсонская область"}


def normalize(name):
    """Нормализация для сопоставления (без типа)."""
    n = name.strip().lower()
    for w in ['муниципальный район', 'муниципальный округ', 'городской округ', 'район', 'округ',
              'городской', 'город', 'зато', 'муниципальный', 'внутригородское муниципальное образование',
              'внутригородской муниципальный округ', 'муниципальное образование', 'поселение',
              'национальный', 'эвенкийский', 'улус', 'кожуун']:
        n = n.replace(w, '')
    n = n.replace('ё', 'е').replace('-', '').replace(' ', '').replace('«', '').replace('»', '').replace('"', '')
    return n.strip()


def fetch_oktmo_page(code):
    """Загрузка страницы ОКТМО по коду региона."""
    url = f"https://okp-okpd.ru/oktmo.aspx?kod={code}"
    try:
        r = requests.get(url, timeout=25)
        r.encoding = 'windows-1251'
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, 'html.parser')
        out = []
        for tr in soup.find_all('tr'):
            cells = tr.find_all('td')
            if len(cells) >= 2:
                code_text = cells[0].get_text(strip=True)
                name_text = cells[1].get_text(strip=True)
                if re.match(r'^\d{11}$', code_text) and name_text:
                    out.append({'oktmo': code_text, 'name': name_text})
        return out
    except Exception as e:
        return None


def get_db_districts(region_name):
    """Список районов региона из БД."""
    with ENGINE.connect() as conn:
        row = conn.execute(text("SELECT id FROM regions WHERE name = :name"), {"name": region_name}).fetchone()
        if not row:
            return None
        rows = conn.execute(text("""
            SELECT name FROM districts WHERE region_id = :rid ORDER BY name
        """), {"rid": str(row[0])}).fetchall()
    return [r[0] for r in rows]


def main():
    out_lines = []
    def log(s=""):
        print(s)
        out_lines.append(s)

    log("# Сравнение названий в БД с ОКТМО (официальные названия)")
    log("Источник ОКТМО: https://okp-okpd.ru/oktmo.aspx")
    log()

    regions_list = []
    for code, region_name in sorted(OKTMO_TO_REGION.items()):
        if region_name in SKIP:
            continue
        regions_list.append((code, region_name, None))
    for ao_name, cfg in AUTONOMOUS_OKRUGS.items():
        if ao_name in SKIP:
            continue
        regions_list.append((cfg["parent_code"], ao_name, cfg["prefix"]))

    total_ok = 0
    total_mismatch = 0
    total_only_oktmo = 0
    total_only_db = 0
    failed_regions = []

    for code, region_name, prefix in regions_list:
        db_names = get_db_districts(region_name)
        if db_names is None:
            continue

        if code not in _cache:
            raw = fetch_oktmo_page(code)
            time.sleep(0.8)
            if raw is None:
                failed_regions.append(region_name)
                continue
            _cache[code] = raw
        all_oktmo = _cache[code]

        if prefix:
            oktmo_entries = [d for d in all_oktmo if d["oktmo"].startswith(prefix)]
        elif region_name == "Архангельская область":
            oktmo_entries = [d for d in all_oktmo if not d["oktmo"].startswith("118")]
        elif region_name == "Тюменская область":
            oktmo_entries = [d for d in all_oktmo if not d["oktmo"].startswith("711") and not d["oktmo"].startswith("7114")]
        else:
            oktmo_entries = all_oktmo

        oktmo_names = [d["name"] for d in oktmo_entries]
        oktmo_by_norm = {normalize(n): n for n in oktmo_names}
        db_by_norm = {normalize(n): n for n in db_names}

        exact = []
        mismatch = []
        only_oktmo = []
        only_db = []

        for o_name in oktmo_names:
            norm = normalize(o_name)
            if norm in db_by_norm:
                db_name = db_by_norm[norm]
                if db_name == o_name:
                    exact.append(o_name)
                else:
                    mismatch.append((db_name, o_name))
            else:
                only_oktmo.append(o_name)

        for d_name in db_names:
            if normalize(d_name) not in oktmo_by_norm:
                only_db.append(d_name)

        total_ok += len(exact)
        total_mismatch += len(mismatch)
        total_only_oktmo += len(only_oktmo)
        total_only_db += len(only_db)

        if mismatch or only_oktmo or only_db:
            log(f"## {region_name}")
            log()
            if mismatch:
                log("### Отличие формулировки (в ОКТМО иначе):")
                for db_n, oktmo_n in mismatch[:25]:
                    log(f"- БД: `{db_n}`")
                    log(f"  ОКТМО: `{oktmo_n}`")
                if len(mismatch) > 25:
                    log(f"- ... и ещё {len(mismatch) - 25}")
                log()
            if only_oktmo:
                log("### Только в ОКТМО (нет в БД):")
                for n in only_oktmo[:15]:
                    log(f"- {n}")
                if len(only_oktmo) > 15:
                    log(f"- ... и ещё {len(only_oktmo) - 15}")
                log()
            if only_db:
                log("### Только в БД (нет в ОКТМО):")
                for n in only_db[:15]:
                    log(f"- {n}")
                if len(only_db) > 15:
                    log(f"- ... и ещё {len(only_db) - 15}")
                log()
            log("---")
            log()

    log()
    log("## Итог по всем регионам")
    log(f"- Совпадает с ОКТМО: **{total_ok}**")
    log(f"- Отличие формулировки: **{total_mismatch}**")
    log(f"- Только в ОКТМО (нет в БД): **{total_only_oktmo}**")
    log(f"- Только в БД (нет в ОКТМО): **{total_only_db}**")
    if failed_regions:
        log(f"- Не удалось загрузить ОКТМО: {', '.join(failed_regions)}")

    report_path = os.path.join(os.path.dirname(__file__), "..", "docs", "OKTMO_COMPARISON_REPORT.md")
    try:
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(out_lines))
        print(f"\nОтчёт сохранён: {report_path}")
    except Exception as e:
        print(f"\nНе удалось сохранить файл: {e}")


_cache = {}

if __name__ == "__main__":
    main()
