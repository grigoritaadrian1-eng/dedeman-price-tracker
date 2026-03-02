import os
import pandas as pd
import streamlit as st
import plotly.express as px

DATA = "dedeman_full_dataset_all.csv"          # <- asta e fișierul tău complet
REPORT = "dedeman_all_weekly_report.csv"

st.set_page_config(page_title="Dedeman Tracker", layout="wide")
st.title("Dedeman — Price Tracker (ALL 893)")

if not os.path.exists(DATA):
    st.error(f"Nu găsesc {DATA}. Generează-l cu: python3 dedeman_merge_prices_attrs_all.py")
    st.stop()

df = pd.read_csv(DATA)

# normalize: trim și NA
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

# discount filter
if only_discount and ("special_price" in f.columns) and ("price" in f.columns):
    p = pd.to_numeric(f["price"], errors="coerce")
    sp = pd.to_numeric(f["special_price"], errors="coerce")
    f = f[(sp.notna()) & (p.notna()) & (sp < p)]

# KPIs
k1, k2, k3, k4 = st.columns(4)
k1.metric("Produse (filtrat)", len(f))
k2.metric("Brand-uri", f["brand"].replace("NA", pd.NA).dropna().nunique())
k3.metric("Dimensiuni", f["size"].replace("NA", pd.NA).dropna().nunique())
k4.metric("Finisaje", f["finish"].replace("NA", pd.NA).dropna().nunique())

# Charts
c1, c2 = st.columns(2)
with c1:
    st.subheader("Distribuție preț (RON)")
    prices = pd.to_numeric(f["price"], errors="coerce").dropna()
    fig = px.histogram(prices, nbins=40)
    st.plotly_chart(fig, use_container_width=True)

with c2:
    st.subheader("Disponibilitate (count)")
    s = f["availability_status"].fillna("NA").value_counts().reset_index()
    s.columns = ["availability_status", "count"]
    fig2 = px.bar(s, x="availability_status", y="count")
    st.plotly_chart(fig2, use_container_width=True)

# Top brands
st.subheader("Top branduri (după număr produse)")
b = f["brand"].value_counts().reset_index()
b.columns = ["brand", "count"]
b = b[b["brand"] != "NA"].head(20)
st.plotly_chart(px.bar(b, x="brand", y="count"), use_container_width=True)

# Table
st.subheader("Tabel produse")
cols = [c for c in ["sku","brand","size","finish","wear_resistance","price","special_price","availability_status","url"] if c in f.columns]
st.dataframe(f[cols], use_container_width=True, height=520)

# Weekly report
st.divider()
st.subheader("Schimbări săptămânale (vs last)")

if os.path.exists(REPORT):
    rep = pd.read_csv(REPORT)
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
else:
    st.info("Încă nu există report săptămânal. Se generează după a 2-a rulare săptămânală.")
