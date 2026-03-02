import re
import pandas as pd
import httpx
from lxml import etree
from io import BytesIO

ROBOTS_URL = "https://www.dedeman.ro/robots.txt"

KEYWORDS = [
    "/gresie", "/faianta", "/gresie-", "/faianta-",
    "gresie", "faianta"
]

def fetch_text(url: str) -> str:
    headers = {"User-Agent": "Mozilla/5.0"}
    with httpx.Client(headers=headers, timeout=60.0, follow_redirects=True) as client:
        r = client.get(url)
        r.raise_for_status()
        return r.text

def fetch_bytes(url: str) -> bytes:
    headers = {"User-Agent": "Mozilla/5.0"}
    with httpx.Client(headers=headers, timeout=60.0, follow_redirects=True) as client:
        r = client.get(url)
        r.raise_for_status()
        return r.content

def parse_sitemap(xml_bytes: bytes) -> list[str]:
    doc = etree.parse(BytesIO(xml_bytes))
    root = doc.getroot()
    return [el.text.strip() for el in root.iter() if el.tag.endswith("loc") and el.text]

def is_relevant(url: str) -> bool:
    u = url.lower()
    if "/p/" not in u:
        return False
    return any(k in u for k in KEYWORDS)

def sku_from_url(url: str) -> str | None:
    m = re.search(r"/p/(\d+)", url)
    return m.group(1) if m else None

def get_sitemaps_from_robots() -> list[str]:
    robots = fetch_text(ROBOTS_URL)
    sitemaps = []
    for line in robots.splitlines():
        if line.lower().startswith("sitemap:"):
            sitemaps.append(line.split(":", 1)[1].strip())
    return sitemaps

def main():
    print("Reading robots.txt for sitemap urls...")
    sitemaps = get_sitemaps_from_robots()
    print(f"Found {len(sitemaps)} sitemap urls in robots.txt")
    for sm in sitemaps:
        print("  ", sm)

    if not sitemaps:
        raise RuntimeError("Nu am găsit nicio linie Sitemap: în robots.txt")

    # Uneori robots listează direct sitemap index, alteori sitemapuri individuale
    # Le parcurgem pe rând și colectăm URL-uri relevante
    all_product_urls = []
    MAX_SITEMAPS = 30

    for i, sm_url in enumerate(sitemaps[:MAX_SITEMAPS], start=1):
        try:
            xml = fetch_bytes(sm_url)
            locs = parse_sitemap(xml)

            # Dacă e sitemap index, locs sunt alte sitemap-uri
            # Dacă e sitemap urlset, locs sunt URL-uri de pagini
            if any("sitemap" in u.lower() for u in locs[:5]):
                # pare index
                inner = [u for u in locs if "sitemap" in u.lower()]
                print(f"[{i}] index -> {len(inner)} inner sitemaps (scan limited)")
                # scanăm câteva inner sitemaps
                for j, inner_url in enumerate(inner[:10], start=1):
                    try:
                        inner_xml = fetch_bytes(inner_url)
                        inner_locs = parse_sitemap(inner_xml)
                        rel = [u for u in inner_locs if is_relevant(u)]
                        all_product_urls.extend(rel)
                        print(f"   - [{j}/10] -> {len(rel)} relevant urls")
                    except Exception as e:
                        print(f"   - [{j}] ERROR inner sitemap: {e}")
            else:
                # pare urlset
                rel = [u for u in locs if is_relevant(u)]
                all_product_urls.extend(rel)
                print(f"[{i}] urlset -> {len(rel)} relevant urls")

        except Exception as e:
            print(f"[{i}] ERROR on sitemap: {sm_url} -> {e}")

    all_product_urls = sorted(set(all_product_urls))
    rows = []
    for u in all_product_urls:
        sku = sku_from_url(u)
        if sku:
            rows.append({"site": "Dedeman", "sku": sku, "url": u})

    df = pd.DataFrame(rows)
    df.to_csv("dedeman_products.csv", index=False)
    print(f"\nSaved dedeman_products.csv with {len(df)} products")

if __name__ == "__main__":
    main()
