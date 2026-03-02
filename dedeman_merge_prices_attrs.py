import pandas as pd
import re

PRICES = "dedeman_bulk_prices.csv"
ATTRS = "dedeman_attrs.csv"
OUT = "dedeman_full_dataset.csv"

def sku_from_url(url: str) -> str | None:
    m = re.search(r"/p/(\d+)", str(url))
    return m.group(1) if m else None

def main():
    prices = pd.read_csv(PRICES)
    attrs = pd.read_csv(ATTRS)

    # IMPORTANT: tipuri consistente pentru merge
    prices["sku"] = prices["sku"].astype(str)
    attrs["sku"] = attrs["url"].apply(sku_from_url).astype(str)

    attrs = attrs.dropna(subset=["sku"]).drop_duplicates(subset=["sku"])

    full = prices.merge(
        attrs[["sku", "brand", "size", "finish", "wear_resistance", "page_title"]],
        on="sku",
        how="left"
    )

    full.to_csv(OUT, index=False)
    print("Saved", OUT)
    print(full.head(10).to_string(index=False))

if __name__ == "__main__":
    main()
