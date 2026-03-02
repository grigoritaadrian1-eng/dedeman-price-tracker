import os
from datetime import datetime, timezone
import pandas as pd

from dedeman_fetch_bulk_all import main as fetch_all_main

PRICES_ALL = "dedeman_bulk_prices_all.csv"          # snapshot curent (893)
LAST_ALL   = "dedeman_all_last.csv"                 # snapshot anterior
HIST_ALL   = "dedeman_all_history.csv"              # istoric (append)
REPORT_ALL = "dedeman_all_weekly_report.csv"        # schimbări vs last

def main():
    # 1) regenerează snapshot-ul de prețuri (ALL)
    fetch_all_main()

    # 2) încarcă snapshot nou + timestamp
    new = pd.read_csv(PRICES_ALL)
    now = datetime.now(timezone.utc).isoformat()
    new["checked_at_utc"] = now

    # 3) append în history
    if os.path.exists(HIST_ALL):
        hist = pd.read_csv(HIST_ALL)
        hist = pd.concat([hist, new], ignore_index=True)
    else:
        hist = new
    hist.to_csv(HIST_ALL, index=False)

    # 4) dacă e prima rulare, doar salvează last
    if not os.path.exists(LAST_ALL):
        new.drop(columns=["checked_at_utc"]).to_csv(LAST_ALL, index=False)
        print("Prima rulare ALL: am creat last + history.")
        return

    last = pd.read_csv(LAST_ALL)

    # 5) comparăm (preț, special, stoc)
    cols = ["sku", "price", "special_price", "availability_status"]
    new_s = new[cols].copy()
    last_s = last[cols].copy()

    merged = new_s.merge(last_s, on="sku", how="left", suffixes=("_new", "_old"))

    changed = merged[
        (merged["price_new"] != merged["price_old"]) |
        (merged["special_price_new"] != merged["special_price_old"]) |
        (merged["availability_status_new"] != merged["availability_status_old"])
    ].copy()

    if changed.empty:
        print("Nicio schimbare față de ultima rulare (ALL).")
    else:
        changed["delta_price"] = changed["price_new"] - changed["price_old"]
        changed = changed.sort_values("delta_price")
        changed["checked_at_utc"] = now
        changed.to_csv(REPORT_ALL, index=False)
        print(f"Schimbări detectate: {len(changed)} | Saved report: {REPORT_ALL}")

    # 6) update last (fără timestamp)
    new.drop(columns=["checked_at_utc"]).to_csv(LAST_ALL, index=False)
    print("Am actualizat ALL last + history.")

if __name__ == "__main__":
    main()
