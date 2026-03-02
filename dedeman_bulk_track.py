import os
from datetime import datetime, timezone
import pandas as pd
from dedeman_fetch_bulk import main as bulk_fetch_main

NEW_FILE = "dedeman_bulk_prices.csv"
LAST_FILE = "dedeman_bulk_last.csv"
HIST_FILE = "dedeman_bulk_history.csv"

def main():
    bulk_fetch_main()  # regenerează dedeman_bulk_prices.csv
    new = pd.read_csv(NEW_FILE)
    new["checked_at_utc"] = datetime.now(timezone.utc).isoformat()

    # history append
    if os.path.exists(HIST_FILE):
        hist = pd.read_csv(HIST_FILE)
        hist = pd.concat([hist, new], ignore_index=True)
    else:
        hist = new
    hist.to_csv(HIST_FILE, index=False)

    # first run
    if not os.path.exists(LAST_FILE):
        new.drop(columns=["checked_at_utc"]).to_csv(LAST_FILE, index=False)
        print("Prima rulare: am salvat dedeman_bulk_last.csv + dedeman_bulk_history.csv")
        return

    last = pd.read_csv(LAST_FILE)

    cols = ["sku", "price", "special_price", "availability_status"]
    merged = new[cols].merge(last[cols], on="sku", how="left", suffixes=("_new", "_old"))

    changed = merged[
        (merged["price_new"] != merged["price_old"]) |
        (merged["special_price_new"] != merged["special_price_old"]) |
        (merged["availability_status_new"] != merged["availability_status_old"])
    ].copy()

    if changed.empty:
        print("Nicio schimbare față de ultima rulare.")
    else:
        # calc diferențe
        changed["delta_price"] = changed["price_new"] - changed["price_old"]
        changed = changed.sort_values("delta_price")
        print("\nTop scăderi (primele 10):")
        print(changed.head(10).to_string(index=False))
        print("\nTop creșteri (ultimele 10):")
        print(changed.tail(10).to_string(index=False))

    # update last
    new.drop(columns=["checked_at_utc"]).to_csv(LAST_FILE, index=False)
    print("\nAm actualizat last + history.")

if __name__ == "__main__":
    main()
