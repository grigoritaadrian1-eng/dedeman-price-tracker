import os
import pandas as pd
import streamlit as st
import plotly.express as px

LOCAL_DATA = "dedeman_full_dataset_all.csv"

st.set_page_config(page_title="Dedeman Tracker", layout="wide")
st.title("Dedeman — Price Tracker (ALL 893)")

# ----- Secrets / ENV -----
def get_secret(name: str) -> str:
    try:
        return str(st.secrets.get(name, "")).strip()
    except Exception:
        return os.getenv(name, "").strip()

DATA_URL = get_secret("DATA_URL")
REPORT_URL = get_secret("REPORT_URL")

# ----- Loaders -----
@st.cache_data(ttl=3600)
def load_data():
    if DATA_URL:
        return pd.read_csv(DATA_URL)
    if os.path.exists(LOCAL_DATA):
        return pd.read_csv(LOCAL_DATA)
    raise FileNotFoundError(
        f"Nu găsesc {LOCAL_DATA} și nici DATA_URL nu e setat. "
        f"Setează DATA_URL în Streamlit Secrets."
    )

@st.cache_data(ttl=3600)
def load_report():
    if REPORT_URL:
        return pd.read_csv(REPORT_URL)
    return None

# ----- Load dataset -----
try:
    df = load_data()
except Exception as e:
    st.error(str(e))
    st.stop()

# normalize
for col in ["brand", "size", "finish", "wear_resistance", "availability_status"]:
    if col in df.columns:
        df[col] = df[col].astype(str).str.strip()
        df.loc[df[col].isin(["", "None", "nan"]), col] = "NA"
        df[col] = df[col].fillna("NA")

def opts(col):
    if col not in df.columns:
        return []
    s = df[col].astype(str).str.strip()
    s = s[~s.isin(["NA", "", "None", "nan"])]
    return sorted(s.unique())

# ----- Sidebar filters -----
st.sidebar.header("Filtre")
brand = st.sidebar.multiselect("Brand", opts("brand"))
size = st.sidebar.multiselect("Dimensiune", opts("size"))
finish = st.sidebar.multiselect("Finisaj", opts("finish"))
wear = st.sidebar.multiselect("Uzură / PEI", opts("wear_resistance"))
avail = st.sidebar.multiselect("Disponibilitate", opts("availability_status"))
only_discount = st.sidebar.checkbox("Doar produse cu reducere (special_price < price)", value=False)

f = df.copy()
if brand: f = f[f["brand"].isin(brand)]
if size: f = f[f["size"].isin(size)]
if finish: f = f[f["finish"].isin(finish)]
if wear: f = f[f["wear_resistance"].isin(wear)]
if avail: f = f[f["availability_status"].isin(avail)]

# discount filter
if only_discount and ("special_price" in f.columns) and ("price" in f.columns):
    p = pd.to_numeric(f["price"], errors="coerce")
    sp = pd.to_numeric(f["special_price"], errors="coerce")
    f = f[(sp.notna()) & (p.notna()) & (sp < p)]

# ----- KPIs -----
k1, k2, k3, k4 = st.columns(4)
k1.metric("Produse (filtrat)", len(f))
k2.metric("Brand-uri", f["brand"].replace("NA", pd.NA).dropna().nunique() if "brand" in f.columns else 0)
k3.metric("Dimensiuni", f["size"].replace("NA", pd.NA).dropna().nunique() if "size" in f.columns else 0)
k4.metric("Finisaje", f["finish"].replace("NA", pd.NA).dropna().nunique() if "finish" in f.columns else 0)

# ----- Charts -----
c1, c2 = st.columns(2)
with c1:
    st.subheader("Distribuție preț (RON)")
    prices = pd.to_numeric(f["price"], errors="coerce").dropna() if "price" in f.columns else pd.Series([])
    st.plotly_chart(px.histogram(prices, nbins=40), use_container_width=True)

with c2:
    st.subheader("Disponibilitate (count)")
    if "availability_status" in f.columns:
        s = f["availability_status"].fillna("NA").value_counts().reset_index()
        s.columns = ["availability_status", "count"]
        st.plotly_chart(px.bar(s, x="availability_status", y="count"), use_container_width=True)
    else:
        st.info("Nu există availability_status în dataset.")

# Brand + Size charts
b1, b2 = st.columns(2)
with b1:
    st.subheader("Top branduri (după număr produse)")
    if "brand" in f.columns:
        b = f["brand"].value_counts().reset_index()
        b.columns = ["brand", "count"]
        b = b[b["brand"] != "NA"].head(20)
        st.plotly_chart(px.bar(b, x="brand", y="count"), use_container_width=True)
    else:
        st.info("Nu există brand în dataset.")

with b2:
    st.subheader("Top dimensiuni (după număr produse)")
    if "size" in f.columns:
        sizes = f["size"].fillna("NA").astype(str).str.strip()
        sizes = sizes[~sizes.isin(["NA", "", "None", "nan"])]
        sz = sizes.value_counts().head(20).reset_index()
        sz.columns = ["size", "count"]
        st.plotly_chart(px.bar(sz, x="size", y="count"), use_container_width=True)
    else:
        st.info("Nu există size în dataset.")

# ----- Table -----
st.subheader("Tabel produse")
cols = [c for c in ["sku","brand","size","finish","wear_resistance","price","special_price","availability_status","url"] if c in f.columns]
st.dataframe(f[cols], use_container_width=True, height=520)

# ----- Weekly changes (from REPORT_URL) -----
st.divider()
st.subheader("Schimbări săptămânale (vs last)")

rep = load_report()
if rep is None:
    st.info("REPORT_URL nu e setat sau nu poate fi citit. Pune REPORT_URL în Secrets (Drive direct download).")
else:
    st.write(f"Schimbări detectate: **{len(rep)}**")

    if "delta_price" in rep.columns:
        rep["delta_price"] = pd.to_numeric(rep["delta_price"], errors="coerce")

    r1, r2 = st.columns(2)
    with r1:
        st.write("Top scăderi (20)")
        st.dataframe(rep.sort_values("delta_price").head(20), use_container_width=True)
    with r2:
        st.write("Top creșteri (20)")
        st.dataframe(rep.sort_values("delta_price").tail(20), use_container_width=True)

st.caption("Data source: " + (DATA_URL if DATA_URL else f"local file {LOCAL_DATA}"))
if REPORT_URL:
    st.caption("Report source: " + REPORT_URL)
