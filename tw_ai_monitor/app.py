import streamlit as st
import requests
import pandas as pd
from collections import deque

st.set_page_config(page_title="V9 Trading System", layout="wide")

# =========================
# SIDEBAR
# =========================
st.sidebar.title("⚙️ 控制台")

api_key = st.sidebar.text_input("API KEY", type="password")
stock = st.sidebar.text_input("股票代碼", "2330")
refresh = st.sidebar.slider("更新頻率(秒)", 1, 10, 2)

# =========================
# SESSION STATE
# =========================
if "hist" not in st.session_state:
    st.session_state.hist = deque(maxlen=80)

if "last_stock" not in st.session_state:
    st.session_state.last_stock = stock

# 換股清空走勢
if st.session_state.last_stock != stock:
    st.session_state.hist = deque(maxlen=80)
    st.session_state.last_stock = stock


# =========================
# Fugle Normalize（關鍵修正）
# =========================
def normalize_fugle(resp):
    if not isinstance(resp, dict):
        return {}

    data = resp.get("data", {})
    quote = data.get("quote", data)

    return {
        "name": data.get("name", stock),
        "price": quote.get("closePrice") or quote.get("lastPrice", 0),
        "vwap": quote.get("avgPrice", 0),
        "high": quote.get("highPrice", 0),
        "low": quote.get("lowPrice", 0),
        "bids": quote.get("bids", []),
        "asks": quote.get("asks", [])
    }


# =========================
# API
# =========================
def get_quote(stock, api_key):
    url = f"https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/{stock}"
    r = requests.get(url, headers={"X-API-KEY": api_key})
    return normalize_fugle(r.json())


# =========================
# 主力偵測 V9
# =========================
def detect_institution(d):
    bids = d.get("bids", [])[:5]
    asks = d.get("asks", [])[:5]

    bid_vol = sum(x.get("size", 0) for x in bids)
    ask_vol = sum(x.get("size", 0) for x in asks)

    imbalance = (bid_vol - ask_vol) / max(1, bid_vol + ask_vol)

    big_buy = any(x.get("size", 0) > 800 for x in bids)
    big_sell = any(x.get("size", 0) > 800 for x in asks)

    return imbalance, big_buy, big_sell


# =========================
# ENGINE
# =========================
def v9_engine(d):
    price = d.get("price", 0)
    vwap = d.get("vwap", 0)
    high = d.get("high", 0)
    low = d.get("low", 0)

    imbalance, big_buy, big_sell = detect_institution(d)

    if price > vwap and imbalance > 0.15 and big_buy:
        signal = "📈 主力進場（多方）"
        reason = "VWAP上 + 買單強 + 大單進場"
        stop = vwap
        tp = high

    elif price < vwap and imbalance < -0.15 and big_sell:
        signal = "📉 主力出貨（空方）"
        reason = "VWAP下 + 賣壓 + 大單出貨"
        stop = vwap
        tp = low

    elif big_buy:
        signal = "⚠️ 主力吸籌"
        reason = "大單買進"
        stop = low
        tp = high

    elif big_sell:
        signal = "⚠️ 主力出貨"
        reason = "大單賣壓"
        stop = high
        tp = low

    else:
        signal = "⛔ 無訊號"
        reason = "盤整"
        stop = None
        tp = None

    return signal, reason, stop, tp, imbalance


# =========================
# MAIN
# =========================
if not api_key:
    st.warning("請輸入 API KEY")
    st.stop()

d = get_quote(stock, api_key)

if not d:
    st.error("API 無資料")
    st.stop()

# update history
if d.get("price"):
    st.session_state.hist.append(d["price"])


# =========================
# STOCK NAME（只顯示股名）
# =========================
stock_name = d.get("name", stock)
st.title(f"⚡ {stock_name}")


# =========================
# TOP METRICS
# =========================
c1, c2, c3, c4 = st.columns(4)

c1.metric("現價", d.get("price", 0))
c2.metric("VWAP", d.get("vwap", 0))
c3.metric("高點", d.get("high", 0))
c4.metric("低點", d.get("low", 0))


# =========================
# SIGNAL
# =========================
signal, reason, stop, tp, imb = v9_engine(d)

st.markdown("## 🤖 V9 主力交易訊號")
st.success(signal)
st.write(reason)

st.markdown("### 🛑 停損 / 停利")
st.write("停損:", stop)
st.write("停利:", tp)


# =========================
# 五檔（三竹風格）
# =========================
st.markdown("## 📊 五檔報價（Level 2）")

colA, colB = st.columns(2)

with colA:
    st.markdown("### 🟢 買盤")
    for b in d.get("bids", [])[:5]:
        st.write(f"{b.get('price')} | {b.get('size')}")

with colB:
    st.markdown("### 🔴 賣盤")
    for a in d.get("asks", [])[:5]:
        st.write(f"{a.get('price')} | {a.get('size')}")


# =========================
# 主力力道
# =========================
st.markdown("## 📈 主力力道")
st.progress(min(1.0, max(0.0, (imb + 1) / 2)))
st.write("Imbalance:", round(imb, 3))


# =========================
# CHART
# =========================
st.markdown("## 📉 即時走勢")

df = pd.DataFrame(list(st.session_state.hist), columns=[stock_name])
st.line_chart(df)
