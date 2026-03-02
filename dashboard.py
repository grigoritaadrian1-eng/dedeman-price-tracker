import os
import pandas as pd
import streamlit as st
import plotly.express as px

LOCAL_DATA = "dedeman_full_dataset_all.csv"
REPORT = "dedeman_all_weekly_report.csv"

st.set_page_config(page_title="Dedeman Tracker", layout="wide")
st.title("Dedeman — Price Tracker (ALL 893)")

# Ia DATA_URL din Streamlit Secrets (Cloud) sau din env (local), fallback pe fișier local
DATA_URL = ""
try:
    DATA_URL = st.secrets.get("DATA_URL", "").strip()
except Exception:
    DATA_URL = ""

if not DATA_URL:
    DATA_URL = os.getenv("DATA_URL", "").strip()

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

if only_discount and ("special_price" in f.columns) and ("price" in f.columns):
    p = pd.to_numeric(f["price"], errors="coerce")
    sp = pd.to_numeric(f["special_price"], errors="coerce")
    f = f[(sp.notna()) & (p.notna()) & (sp < p)]

k1, k2, k3, k4 = st.columns(4)
k1.metric("Produse (filtrat)", len(f))
k2.metric("Brand-uri", f["brand"].replace("NA", pd.NA).dropna().nunique())
k3.metric("Dimensiuni", f["size"].replace("NA", pd.NA).dropna().nunique())
k4.metric("Finisaje", f["finish"].replace("NA", pd.NA).dropna().nunique())

c1, c2 = st.columns(2)
with c1:
    st.subheader("Distribuție preț (RON)")
    prices = pd.to_numeric(f["price"], errors="coerce").dropna()
    st.plotly_chart(px.histogram(prices, nbins=40), use_container_width=True)

with c2:
    st.subheader("Disponibilitate (count)")
    s = f["availability_status"].fillna("NA").value_counts().reset_index()
    s.columns = ["availability_status", "count"]
    st.plotly_chart(px.bar(s, x="availability_status", y="count"), use_container_width=True)

st.subheader("Top branduri (după număr produse)")
b = f["brand"].value_counts().reset_index()
b.columns = ["brand", "count"]
b = b[b["brand"] != "NA"].head(20)
st.plotly_chart(px.bar(b, x="brand", y="count"), use_container_width=True)

st.subheader("Tabel produse")
cols = [c for c in ["sku","brand","size","finish","wear_resistance","price","special_price","availability_status","url"] if c in f.columns]
st.dataframe(f[cols], use_container_width=True, height=520)

st.caption("Data source: " + (DATA_URL if DATA_URL else f"local file {LOCAL_DATA}"))
