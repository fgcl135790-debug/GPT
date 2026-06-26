import streamlit as st
import requests

st.set_page_config(page_title="TW AI Monitor v3 Stable", layout="wide")

st.title("TW AI Monitor v3 Stable")

# =========================
# INPUT
# =========================
api_key = st.text_input("Fugle API Key", type="password")
symbol = st.text_input("股票代碼", value="2330")

# =========================
# CLEAN KEY
# =========================
def clean_key(key):
    return str(key).strip().replace("\n", "").replace("\r", "").replace(" ", "")

# =========================
# API CALL
# =========================
def get_snapshot(api_key, symbol):
    url = f"https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/{symbol}"

    headers = {
        "X-API-KEY": clean_key(api_key)
    }

    try:
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()

        return data

    except Exception as e:
        st.error("API request failed")
        st.write(e)
        return None

# =========================
# MAIN
# =========================
if st.button("開始監控"):

    if not api_key:
        st.warning("請輸入 API Key")
        st.stop()

    data = get_snapshot(api_key, symbol)

    if not data:
        st.error("沒有回傳資料")
        st.stop()

    # =========================
    # PRICE
    # =========================
    price = data.get("lastPrice")
    change = data.get("change")
    change_percent = data.get("changePercent")

    st.subheader(f"{data.get('name')} ({symbol})")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("價格", price)

    with col2:
        st.metric("漲跌", change)

    with col3:
        st.metric("漲跌幅", change_percent)

    # =========================
    # ORDER BOOK
    # =========================
    st.subheader("五檔報價")

    bids = data.get("bids", [])
    asks = data.get("asks", [])

    col1, col2 = st.columns(2)

    with col1:
        st.write("買方")
        for b in bids:
            st.write(f"{b['price']} | {b['size']}")

    with col2:
        st.write("賣方")
        for a in asks:
            st.write(f"{a['price']} | {a['size']}")

    # =========================
    # RAW DATA
    # =========================
    with st.expander("RAW JSON"):
        st.json(data)
