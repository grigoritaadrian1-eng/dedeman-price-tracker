import os
from datetime import datetime, timezone
import pandas as pd

from dedeman_fetch_bulk import main as bulk_fetch_main

NEW_FILE = "dedeman_bulk_prices.csv"          # generat de dedeman_fetch_bulk.py (tiles only acum)
LAST_FILE = "dedeman_tiles_last.csv"          # snapshot pentru plăci
HIST_FILE = "dedeman_tiles_history.csv"       # istoric pentru plăci
REPORT_FILE = "dedeman_tiles_report.csv"      # raport “azi”

def main():
    # 1) regenerează dedeman_bulk_prices.csv (tiles only)
    bulk_fetch_main()

    # 2) citește noul snapshot
    new = pd.read_csv(NEW_FILE)
    now = datetime.now(timezone.utc).isoformat()
    new["checked_at_utc"] = now

    # 3) append în history
    if os.path.exists(HIST_FILE):
        hist = pd.read_csv(HIST_FILE)
        hist = pd.concat([hist, new], ignore_index=True)
    else:
        hist = new
    hist.to_csv(HIST_FILE, index=False)

    # 4) prima rulare: doar salvează LAST
    if not os.path.exists(LAST_FILE):
        new.drop(columns=["checked_at_utc"]).to_csv(LAST_FILE, index=False)
        print("Prima rulare (tiles): am creat last + history.")
        return

    last = pd.read_csv(LAST_FILE)

    # 5) detectare schimbări
    cols = ["sku", "price", "special_price", "availability_status"]
    merged = new[cols].merge(last[cols], on="sku", how="left", suffixes=("_new", "_old"))

    changed = merged[
        (merged["price_new"] != merged["price_old"]) |
        (merged["special_price_new"] != merged["special_price_old"]) |
        (merged["availability_status_new"] != merged["availability_status_old"])
    ].copy()

    if changed.empty:
        print("Nicio schimbare față de ultima rulare (tiles).")
        # update last și gata
        new.drop(columns=["checked_at_utc"]).to_csv(LAST_FILE, index=False)
        return

    # 6) calc diferențe (pentru sort)
    changed["delta_price"] = changed["price_new"] - changed["price_old"]
    changed["delta_special"] = changed["special_price_new"] - changed["special_price_old"]

    # 7) atașăm URL ca să fie util
    sku_to_url = new[["sku", "url"]].drop_duplicates()
    report = changed.merge(sku_to_url, on="sku", how="left")
    report["checked_at_utc"] = now

    # sort: cele mai mari scăderi primele
    report = report.sort_values("delta_price")
    report.to_csv(REPORT_FILE, index=False)

    print("\nSchimbări detectate (tiles) — top scăderi (10):")
    print(report.head(10)[["sku","price_old","price_new","delta_price","availability_status_old","availability_status_new"]].to_string(index=False))

    print("\nTop creșteri (10):")
    print(report.tail(10)[["sku","price_old","price_new","delta_price","availability_status_old","availability_status_new"]].to_string(index=False))

    print(f"\nSaved report: {REPORT_FILE}")

    # 8) update last
    new.drop(columns=["checked_at_utc"]).to_csv(LAST_FILE, index=False)
    print("Am actualizat tiles last + history.")

if __name__ == "__main__":
    main()
