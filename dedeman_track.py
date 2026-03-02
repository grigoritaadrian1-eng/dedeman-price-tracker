import os
import pandas as pd
from dedeman_fetch import main as fetch_main  # reutilizăm scriptul tău

# 1) rulează fetch ca să regenereze dedeman_output.csv
fetch_main()

NEW_FILE = "dedeman_output.csv"
LAST_FILE = "dedeman_last.csv"

new = pd.read_csv(NEW_FILE)

if not os.path.exists(LAST_FILE):
    new.to_csv(LAST_FILE, index=False)
    print("Prima rulare: am salvat dedeman_last.csv (nu am cu ce compara încă).")
    raise SystemExit(0)

last = pd.read_csv(LAST_FILE)

# comparăm doar câteva coloane relevante
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
    print("Nicio schimbare față de ultima rulare.")
else:
    print("\nSchimbări detectate:")
    print(changed.to_string(index=False))

# update snapshot
new.to_csv(LAST_FILE, index=False)
print("\nAm actualizat dedeman_last.csv")
