import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Fugle Debug Tool")

st.title("Fugle API Debug Console")

# =========================
# INPUT
# =========================
api_key = st.text_input("Fugle API Key", type="password")
symbol = st.text_input("Stock Symbol", value="2330")

# =========================
# CLEAN KEY
# =========================
def clean_key(key):
    if not key:
        return ""
    return str(key).strip().replace("\n", "").replace("\r", "").replace(" ", "")

# =========================
# FETCH API
# =========================
def fetch_data(api_key, symbol):
    url = f"https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/{symbol}"

    headers = {
        "X-API-KEY": clean_key(api_key)
    }

    st.write("DEBUG URL:", url)
    st.write("DEBUG KEY repr:", repr(headers["X-API-KEY"]))

    try:
        res = requests.get(url, headers=headers, timeout=10)

        st.write("STATUS CODE:", res.status_code)
        st.write("RAW TEXT (first 500 chars):")
        st.code(res.text[:500])

        try:
            data = res.json()
        except Exception as e:
            st.error("JSON parse failed")
            st.write(e)
            return None

        return data

    except Exception as e:
        st.error("Request failed")
        st.write(e)
        return None

# =========================
# MAIN
# =========================
if st.button("TEST API"):
    if not api_key:
        st.warning("Please input API key")
        st.stop()

    data = fetch_data(api_key, symbol)

    if data is None:
        st.error("No data returned")
        st.stop()

    st.subheader("JSON KEYS")
    if isinstance(data, dict):
        st.write(list(data.keys()))

    st.subheader("RAW JSON")
    st.json(data)
