import streamlit as st
import requests
import pandas as pd
import time

st.set_page_config(page_title="TW AI Monitor PRO", layout="wide")


# =========================
# FETCH DATA
# =========================
def fetch_data(api_key, symbol):
    url = f"https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/{symbol}"
    headers = {"X-API-KEY": str(api_key).strip()}
    res = requests.get(url, headers=headers, timeout=10)
    return res.json()


# =========================
# INDICATORS (mock)
# =========================
def calc_indicators(price):
    return price, price * 0.999, price * 0.998, price * 1.002


# =========================
# TAIWAN COLOR RULE
# =========================
def tw_color(change):
    if change > 0:
        return "🔴 上漲"
    elif change < 0:
        return "🟢 下跌"
    else:
        return "⚪ 平盤"


# =========================
# SIDEBAR (FIXED AUTO MODE)
# =========================
with st.sidebar:
    st.title("⚙ 控制面板")

    api_key = st.text_input("Fugle API Key", type="password")
    symbol = st.text_input("股票代碼", value="2330")

    refresh_sec = st.slider("更新頻率（秒）", 1, 10, 3)

    st.markdown("---")
    st.markdown(f"### ⏱ 目前更新頻率")
    st.markdown(f"## {refresh_sec} 秒 / 次")

    run = st.button("🚀 開始監控（自動更新）")


# =========================
# PLACEHOLDER (no flicker zone)
# =========================
placeholder = st.empty()


# =========================
# MAIN LOOP (NO FLICKER)
# =========================
if run and api_key and symbol:

    while True:

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

        with placeholder.container():

            # =========================
            # HEADER
            # =========================
            st.markdown(f"## ⚡ {name} ({symbol})")
            st.markdown("### 狀態：" + tw_color(change))

            c1, c2, c3 = st.columns(3)
            c1.metric("價格", price)
            c2.metric("漲跌", change)
            c3.metric("漲跌幅", f"{change_pct}%")


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
                    df = pd.DataFrame(bids)
                    st.dataframe(df.rename(columns={"price": "價格", "size": "張數"}))
                else:
                    st.write("No data")

            with col2:
                st.markdown("### 🔴 賣方")
                if asks:
                    df = pd.DataFrame(asks)
                    st.dataframe(df.rename(columns={"price": "價格", "size": "張數"}))
                else:
                    st.write("No data")


            # =========================
            # AI SIGNAL
            # =========================
            st.markdown("## 🤖 AI 判斷")

            if change > 0:
                st.success("🔴 偏多（上漲動能）")
            elif change < 0:
                st.error("🟢 偏空（下跌壓力）")
            else:
                st.warning("⚪ 盤整")

        time.sleep(refresh_sec)

else:
    st.info("請輸入 API Key 並按開始監控")
