import re
import json
import pandas as pd
import httpx

CSV_PATH = "target.csv"
PRICE_ENDPOINT = "https://www.dedeman.ro/__price/"

def read_targets(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, sep=";", engine="python")
    df = df.loc[:, ~df.columns.str.contains(r"^Unnamed", na=False)]
    df["Site"] = df["Site"].astype(str).str.strip()
    df["Url"] = df["Url"].astype(str).str.strip()
    return df

def extract_sku_from_url(url: str) -> str | None:
    # Dedeman: .../p/4027461
    m = re.search(r"/p/(\d+)", url)
    return m.group(1) if m else None

def fetch_prices(skus: list[str]) -> dict:
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "https://www.dedeman.ro",
        "Referer": "https://www.dedeman.ro/",
    }
    payload = {"skus": skus, "store": None}

    with httpx.Client(headers=headers, timeout=30.0, follow_redirects=True) as client:
        r = client.post(PRICE_ENDPOINT, json=payload)
        r.raise_for_status()
        return r.json()

def main():
    df = read_targets(CSV_PATH)
    ded = df[df["Site"].str.lower().str.contains("dedeman")].copy()

    ded["sku"] = ded["Url"].apply(extract_sku_from_url)
    ded = ded[ded["sku"].notna()]

    skus = ded["sku"].tolist()
    print(f"Dedeman targets: {len(ded)} | SKUs: {len(skus)}")

    data = fetch_prices(skus)

    rows = []
    for _, row in ded.iterrows():
        sku = row["sku"]
        item = data.get(sku) or {}

        price = item.get("price")
        special_price = item.get("special_price")
        base_unit = item.get("base_unit")
        alt_unit = item.get("alternative_unit")

        avail = item.get("availability") or {}
        avail_status = avail.get("status")
        store = avail.get("store")

        rows.append({
            "site": "Dedeman",
            "sku": sku,
            "url": row["Url"],
            "price": float(price) if price is not None else None,
            "special_price": float(special_price) if special_price is not None else None,
            "availability_status": avail_status,
            "store": store,
            "base_unit": base_unit,
            "alternative_unit": alt_unit,
        })

    out = pd.DataFrame(rows)
    out.to_csv("dedeman_output.csv", index=False)
    print("Saved dedeman_output.csv")

    # print preview
    print(out.head(10).to_string(index=False))

if __name__ == "__main__":
    main()
