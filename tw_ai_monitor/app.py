import streamlit as st
import requests
import pandas as pd
import time

st.set_page_config(page_title="TW AI Monitor PRO", layout="wide")


# =========================
# DATA FETCH
# =========================
def fetch_data(api_key, symbol):
    url = f"https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/{symbol}"
    headers = {"X-API-KEY": str(api_key).strip()}
    res = requests.get(url, headers=headers, timeout=10)
    return res.json()


# =========================
# SIMPLE INDICATORS (mock)
# =========================
def calc_indicators(price):
    ema5 = price
    ema20 = price * 0.999
    ema60 = price * 0.998
    vwap = price * 1.002
    return ema5, ema20, ema60, vwap


# =========================
# TAIWAN COLOR LOGIC
# =========================
def tw_color(change):
    if change > 0:
        return "🔴 上漲"
    elif change < 0:
        return "🟢 下跌"
    else:
        return "⚪ 平盤"


# =========================
# UI
# =========================
st.title("⚡ TW AI Monitor v3 PRO (TW Style)")

api_key = st.text_input("Fugle API Key", type="password")
symbol = st.text_input("股票代碼", value="2330")

colA, colB, colC = st.columns([1, 1, 2])

with colA:
    run = st.button("🚀 開始監控")

with colB:
    auto = st.checkbox("Auto Refresh (3s)")

with colC:
    st.caption("台股配色版本：紅漲綠跌")


# =========================
# AUTO REFRESH
# =========================
if auto:
    time.sleep(3)
    st.rerun()


# =========================
# MAIN
# =========================
if run and api_key and symbol:

    data = fetch_data(api_key, symbol)

    name = data.get("name", symbol)
    price = data.get("lastPrice", 0)
    change = data.get("change", 0)
    change_pct = data.get("changePercent", 0)

    bids = data.get("bids", [])
    asks = data.get("asks", [])

    total = data.get("total", {})
    volume = total.get("tradeVolume", 0)

    ema5, ema20, ema60, vwap = calc_indicators(price)

    # =========================
    # HEADER
    # =========================
    st.markdown(f"## ⚡ {name} ({symbol})")

    c1, c2, c3 = st.columns(3)

    # 台股顏色邏輯（重點）
    c1.metric("價格", price)

    if change > 0:
        c2.metric("漲跌", change, delta_color="inverse")  # red up
        c3.metric("漲跌幅", f"{change_pct}%", delta_color="inverse")
    elif change < 0:
        c2.metric("漲跌", change, delta_color="normal")  # green down
        c3.metric("漲跌幅", f"{change_pct}%", delta_color="normal")
    else:
        c2.metric("漲跌", change)
        c3.metric("漲跌幅", f"{change_pct}%")


    st.markdown("### 📌 狀態：" + tw_color(change))


    # =========================
    # INDICATORS
    # =========================
    st.markdown("## 📊 技術指標")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("VWAP", round(vwap, 2))
    c2.metric("EMA5", round(ema5, 2))
    c3.metric("EMA20", round(ema20, 2))
    c4.metric("EMA60", round(ema60, 2))


    # =========================
    # VOLUME
    # =========================
    st.markdown("## 📦 成交量")
    st.bar_chart([volume])


    # =========================
    # ORDER BOOK
    # =========================
    st.markdown("## 📘 五檔報價")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🟢 買方")
        if bids:
            df_b = pd.DataFrame(bids)
            st.dataframe(df_b.rename(columns={"price": "價格", "size": "張數"}))
        else:
            st.write("No data")

    with col2:
        st.markdown("### 🔴 賣方")
        if asks:
            df_a = pd.DataFrame(asks)
            st.dataframe(df_a.rename(columns={"price": "價格", "size": "張數"}))
        else:
            st.write("No data")


    # =========================
    # AI SIGNAL
    # =========================
    st.markdown("## 🤖 AI 判斷")

    if change > 0:
        st.success("🔴 台股偏多（上漲動能）")
    elif change < 0:
        st.error("🟢 台股偏空（下跌壓力）")
    else:
        st.warning("⚪ 盤整狀態")


    # =========================
    # DEBUG
    # =========================
    with st.expander("RAW JSON"):
        st.json(data)

else:
    st.info("請輸入 API Key 並按開始監控")
