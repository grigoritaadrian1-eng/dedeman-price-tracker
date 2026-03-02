import math
import time
import pandas as pd
import httpx

PRICE_ENDPOINT = "https://www.dedeman.ro/__price/"
INPUT_PRODUCTS = "dedeman_tiles_products.csv"   # <- DOAR placile (gresie/faianta)
OUTPUT_PRICES = "dedeman_bulk_prices.csv"

def chunk(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i+n]

def fetch_prices(client: httpx.Client, skus):
    payload = {"skus": skus, "store": None}
    r = client.post(PRICE_ENDPOINT, json=payload)
    r.raise_for_status()
    return r.json()

def main():
    df = pd.read_csv(INPUT_PRODUCTS)
    df["sku"] = df["sku"].astype(str)

    skus = df["sku"].tolist()
    print(f"Input file: {INPUT_PRODUCTS}")
    print(f"Total SKUs: {len(skus)}")

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "https://www.dedeman.ro",
        "Referer": "https://www.dedeman.ro/",
    }

    BATCH = 250  # poți urca la 300-400 dacă merge ok
    rows = []

    total_batches = math.ceil(len(skus) / BATCH)
    with httpx.Client(headers=headers, timeout=60.0, follow_redirects=True) as client:
        for bi, skus_batch in enumerate(chunk(skus, BATCH), start=1):
            data = fetch_prices(client, skus_batch)
            print(f"[{bi}/{total_batches}] got {len(data)} entries")

            for sku in skus_batch:
                item = data.get(sku) or {}
                avail = item.get("availability") or {}

                rows.append({
                    "sku": sku,
                    "price": float(item["price"]) if item.get("price") is not None else None,
                    "special_price": float(item["special_price"]) if item.get("special_price") is not None else None,
                    "availability_status": avail.get("status"),
                    "store": avail.get("store"),
                    "base_unit": item.get("base_unit"),
                })

            time.sleep(0.3)  # mică pauză, să fim “cuminți”

    out = pd.DataFrame(rows).merge(df[["sku", "url"]], on="sku", how="left")
    out.to_csv(OUTPUT_PRICES, index=False)
    print(f"Saved {OUTPUT_PRICES}")
    print(out.head(10).to_string(index=False))

if __name__ == "__main__":
    main()
