import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="TW AI Monitor", layout="wide")

# =========================
# API FUNCTION
# =========================
def fetch_fugle(api_key: str, symbol: str):
    url = f"https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/{symbol}"

    headers = {
        "X-API-KEY": str(api_key).strip()
    }

    res = requests.get(url, headers=headers, timeout=10)
    data = res.json()
    return data


# =========================
# UI
# =========================
st.title("TW AI Monitor v3 Stable")

api_key = st.text_input("Fugle API Key", type="password")
symbol = st.text_input("股票代碼", value="2330")

start = st.button("開始監控")


# =========================
# MAIN
# =========================
if start and api_key and symbol:

    data = fetch_fugle(api_key, symbol)

    # -------- safe extract --------
    name = data.get("name", symbol)
    last_price = data.get("lastPrice", 0)
    change = data.get("change", 0)
    change_percent = data.get("changePercent", 0)

    bids = data.get("bids", [])
    asks = data.get("asks", [])

    total = data.get("total", {})
    volume = total.get("tradeVolume", 0)
    value = total.get("tradeValue", 0)

    # =========================
    # HEADER
    # =========================
    st.subheader(f"{name} ({symbol})")

    col1, col2, col3 = st.columns(3)

    col1.metric("價格", last_price)
    col2.metric("漲跌", change)
    col3.metric("漲跌幅", f"{change_percent}%")


    # =========================
    # EXTRA STATS (like your 2nd image)
    # =========================
    st.markdown("## 交易資訊")

    col1, col2, col3 = st.columns(3)

    col1.metric("成交量", volume)
    col2.metric("成交金額", value)
    col3.metric("均價", data.get("avgPrice", 0))


    # =========================
    # ORDER BOOK
    # =========================
    st.markdown("## 五檔報價")

    bid_df = pd.DataFrame(bids)
    ask_df = pd.DataFrame(asks)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 買方")
        if not bid_df.empty:
            st.dataframe(bid_df.rename(columns={"price": "價格", "size": "張數"}))
        else:
            st.write("無資料")

    with col2:
        st.markdown("### 賣方")
        if not ask_df.empty:
            st.dataframe(ask_df.rename(columns={"price": "價格", "size": "張數"}))
        else:
            st.write("無資料")


    # =========================
    # RAW DATA (debug)
    # =========================
    with st.expander("RAW JSON"):
        st.json(data)

else:
    st.info("輸入 API Key + 股票代碼，然後按「開始監控」")
