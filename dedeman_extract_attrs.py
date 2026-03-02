import re
import json
import time
import pandas as pd
import httpx
from bs4 import BeautifulSoup

INPUT_PRODUCTS = "dedeman_products.csv"   # 893+ produse
OUTPUT_ATTRS = "dedeman_attrs.csv"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36",
    "Accept-Language": "ro-RO,ro;q=0.9,en;q=0.8",
}

# ---- helpers ----

def fetch_html(client: httpx.Client, url: str) -> str:
    r = client.get(url)
    r.raise_for_status()
    return r.text

def parse_json_ld(soup: BeautifulSoup) -> list[dict]:
    out = []
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        txt = (tag.get_text() or "").strip()
        if not txt:
            continue
        try:
            data = json.loads(txt)
            if isinstance(data, list):
                out.extend([x for x in data if isinstance(x, dict)])
            elif isinstance(data, dict):
                out.append(data)
        except Exception:
            continue
    return out

def get_brand_from_jsonld(jsonlds: list[dict]) -> str | None:
    for obj in jsonlds:
        t = obj.get("@type")
        if t == "Product" or (isinstance(t, list) and "Product" in t):
            b = obj.get("brand")
            if isinstance(b, dict):
                return (b.get("name") or None)
            if isinstance(b, str):
                return b
    return None

def extract_size_from_text(text: str) -> str | None:
    """
    Caută formate tipice: "60 x 120 cm", "33,3 x 90 cm", "20x50 cm"
    """
    t = text.lower().replace("×", "x")
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*x\s*(\d+(?:[.,]\d+)?)\s*cm", t)
    if m:
        a = m.group(1).replace(",", ".")
        b = m.group(2).replace(",", ".")
        return f"{a} x {b} cm"
    return None

def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()

def find_spec_value(soup: BeautifulSoup, labels: list[str]) -> str | None:
    """
    Încearcă să găsească în pagină un câmp de specificații tip label:value.
    Merge pe:
      - tabele (tr/td/th)
      - liste (dt/dd)
      - blocuri text (fallback)
    """
    labels_l = [l.lower() for l in labels]

    # 1) tabel: <tr><th>Label</th><td>Value</td>
    for tr in soup.find_all("tr"):
        cells = tr.find_all(["th", "td"])
        if len(cells) >= 2:
            key = norm(cells[0].get_text(" ", strip=True)).lower()
            val = norm(cells[1].get_text(" ", strip=True))
            if any(lbl in key for lbl in labels_l) and val:
                return val

    # 2) dl/dt/dd
    for dt in soup.find_all("dt"):
        key = norm(dt.get_text(" ", strip=True)).lower()
        if any(lbl in key for lbl in labels_l):
            dd = dt.find_next_sibling("dd")
            if dd:
                val = norm(dd.get_text(" ", strip=True))
                if val:
                    return val

    # 3) fallback: caută “Label ... Value” în text
    text = norm(soup.get_text(" ", strip=True))
    for lbl in labels:
        m = re.search(re.escape(lbl) + r"\s*[:\-]?\s*([A-Za-z0-9 .,/]+)", text, re.IGNORECASE)
        if m:
            val = norm(m.group(1))
            if val and len(val) < 80:
                return val

    return None

def extract_finish(text: str) -> str | None:
    """
    Finisajul la plăci apare des în titlu/spec:
      mata, lucioasa, semilucioasa, satinata, structurata
    """
    t = text.lower()
    hits = []
    for k in ["mata", "lucioasa", "semi-lucioasa", "semilucioasa", "satinata", "structurata"]:
        if k in t:
            hits.append(k.replace("semi-lucioasa", "semilucioasa"))
    # dedupe păstrând ordinea
    if hits:
        uniq = []
        for h in hits:
            if h not in uniq:
                uniq.append(h)
        return ", ".join(uniq)
    return None

def extract_wear_resistance(text: str) -> str | None:
    """
    Rezistența la uzură apare des ca:
      - "PEI 3" / "PEI IV"
      - "clasa de abraziune" / "rezistenta la uzura"
    """
    t = text.upper()
    m = re.search(r"\bPEI\s*([0-9IVX]+)\b", t)
    if m:
        return f"PEI {m.group(1)}"
    return None

# ---- main extraction ----

def extract_attrs_from_url(client: httpx.Client, url: str) -> dict:
    html = fetch_html(client, url)
    soup = BeautifulSoup(html, "lxml")

    jsonlds = parse_json_ld(soup)
    brand = get_brand_from_jsonld(jsonlds)

    # titlul paginii + text pentru pattern-uri
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    page_text = norm(soup.get_text(" ", strip=True))

    # dimensiune: 1) spec 2) titlu/text
    size = find_spec_value(soup, ["Dimensiune", "Dimensiuni", "Format", "Marime", "Mărime"])
    if not size:
        size = extract_size_from_text(title) or extract_size_from_text(page_text)

    # finisaj: 1) spec 2) din title/text
    finish = find_spec_value(soup, ["Finisaj", "Suprafata", "Suprafață"])
    if not finish:
        finish = extract_finish(title) or extract_finish(page_text)

    # rezistență uzură: 1) spec 2) PEI din text
    wear = find_spec_value(soup, ["Rezistenta la uzura", "Rezistența la uzură", "Clasa abraziune", "Clasa de abraziune", "PEI"])
    if not wear:
        wear = extract_wear_resistance(page_text)

    # brand fallback: uneori e “Producator”
    if not brand:
        brand = find_spec_value(soup, ["Brand", "Producator", "Producător"])

    return {
        "url": url,
        "brand": brand,
        "size": size,
        "finish": finish,
        "wear_resistance": wear,
        "page_title": title[:160],
    }

def main():
    df = pd.read_csv(INPUT_PRODUCTS)
    urls = df["url"].astype(str).tolist()
    print(f"Input: {INPUT_PRODUCTS} | URLs: {len(urls)}")

    rows = []
    errors = 0

    with httpx.Client(headers=HEADERS, timeout=60.0, follow_redirects=True) as client:
        for i, url in enumerate(urls, start=1):
            try:
                row = extract_attrs_from_url(client, url)
                rows.append(row)
            except Exception as e:
                errors += 1
                rows.append({"url": url, "brand": None, "size": None, "finish": None, "wear_resistance": None, "page_title": None})
                print(f"[{i}/{len(urls)}] ERROR: {type(e).__name__}: {e}")

            if i % 50 == 0:
                print(f"Processed {i}/{len(urls)} (errors: {errors})")
            time.sleep(0.12)  # polite rate-limit

    out = pd.DataFrame(rows)
    out.to_csv(OUTPUT_ATTRS, index=False)
    print(f"Saved {OUTPUT_ATTRS} | rows: {len(out)} | errors: {errors}")

if __name__ == "__main__":
    main()
