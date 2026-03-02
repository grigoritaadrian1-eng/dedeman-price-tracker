import pandas as pd

INCLUDE = ["//www.dedeman.ro/ro/gresie", "//www.dedeman.ro/ro/faianta", "/ro/gresie", "/ro/faianta"]
EXCLUDE = ["adeziv", "chit", "glet", "amorsa", "spaclu", "silicon", "profil", "distantier", "nivela", "accesori", "disc"]

def main():
    df = pd.read_csv("dedeman_products.csv")
    u = df["url"].str.lower()

    mask_inc = u.apply(lambda x: any(k in x for k in INCLUDE))
    mask_exc = u.apply(lambda x: any(k in x for k in EXCLUDE))

    out = df[mask_inc & (~mask_exc)].copy()
    out.to_csv("dedeman_tiles_products.csv", index=False)

    print("Original:", len(df))
    print("Tiles only:", len(out))
    print("Saved dedeman_tiles_products.csv")

if __name__ == "__main__":
    main()
