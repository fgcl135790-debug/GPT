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
# 股票名稱（標題只顯示這個）
# =========================
stock_name = d.get("name", stock)

# =========================
# session state
# =========================
if "last_stock" not in st.session_state:
    st.session_state.last_stock = stock

if st.session_state.last_stock != stock:
    st.session_state.hist = deque(maxlen=80)
    st.session_state.last_stock = stock

if "hist" not in st.session_state:
    st.session_state.hist = deque(maxlen=80)

# =========================
# API
# =========================
def get_quote(stock, api_key):
    url = f"https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/{stock}"
    r = requests.get(url, headers={"X-API-KEY": api_key})
    d = r.json()

    return {
        "price": d.get("closePrice") or d.get("lastPrice", 0),
        "vwap": d.get("avgPrice", 0),
        "high": d.get("highPrice", 0),
        "low": d.get("lowPrice", 0),
        "bids": d.get("bids", []),
        "asks": d.get("asks", [])
    }

# =========================
# 主力偵測 V9
# =========================
def detect_institution(d):
    bids = d["bids"][:5]
    asks = d["asks"][:5]

    bid_vol = sum(x.get("size", 0) for x in bids)
    ask_vol = sum(x.get("size", 0) for x in asks)

    imbalance = (bid_vol - ask_vol) / max(1, bid_vol + ask_vol)

    big_buy = any(x.get("size", 0) > 800 for x in bids)
    big_sell = any(x.get("size", 0) > 800 for x in asks)

    return imbalance, big_buy, big_sell

# =========================
# V9 TRADING ENGINE
# =========================
def v9_engine(d):
    price = d["price"]
    vwap = d["vwap"]
    high = d["high"]
    low = d["low"]

    imbalance, big_buy, big_sell = detect_institution(d)

    # ================= SIGNAL =================
    if price > vwap and imbalance > 0.15 and big_buy:
        signal = "📈 主力進場（多方）"
        reason = "VWAP上 + 買盤壓制 + 大單進場"
        stop = vwap
        tp = high

    elif price < vwap and imbalance < -0.15 and big_sell:
        signal = "📉 主力出貨（空方）"
        reason = "VWAP下 + 賣壓主導 + 大單倒貨"
        stop = vwap
        tp = low

    elif big_buy and not big_sell:
        signal = "⚠️ 主力吸籌"
        reason = "大單買進但未突破"
        stop = low
        tp = high

    elif big_sell and not big_buy:
        signal = "⚠️ 主力出貨"
        reason = "大單賣壓累積"
        stop = high
        tp = low

    else:
        signal = "⛔ 無明確主力訊號"
        reason = "市場盤整"
        stop = None
        tp = None

    return signal, reason, stop, tp, imbalance

# =========================
# API DATA
# =========================
if not api_key:
    st.warning("請輸入 API KEY")
    st.stop()

d = get_quote(stock, api_key)

st.session_state.hist.append(d["price"])

# =========================
# TITLE（只留股名）
# =========================
st.title(f"⚡ {stock_name}")

# =========================
# TOP METRICS
# =========================
col1, col2, col3, col4 = st.columns(4)

col1.metric("現價", d["price"])
col2.metric("VWAP", d["vwap"])
col3.metric("高點", d["high"])
col4.metric("低點", d["low"])

# =========================
# V9 SIGNAL
# =========================
signal, reason, stop, tp, imb = v9_engine(d)

st.markdown("## 🤖 V9 主力交易訊號")
st.success(signal)
st.write("📌", reason)

st.markdown("### 🛑 停損 / 停利")
st.write("停損:", stop)
st.write("停利:", tp)

# =========================
# 三竹級五檔
# =========================
st.markdown("## 📊 五檔報價（Level 2）")

colA, colB = st.columns(2)

with colA:
    st.markdown("### 🟢 買盤")
    for b in d["bids"][:5]:
        st.write(f"{b.get('price')} | {b.get('size')}")

with colB:
    st.markdown("### 🔴 賣盤")
    for a in d["asks"][:5]:
        st.write(f"{a.get('price')} | {a.get('size')}")

# =========================
# IMBALANCE
# =========================
st.markdown("## 📈 主力力道")
st.progress(min(1.0, max(0.0, (imb + 1) / 2)))
st.write("Imbalance:", round(imb, 3))

# =========================
# CHART
# =========================
st.markdown("## 📉 即時走勢")

st.line_chart(pd.DataFrame(list(st.session_state.hist), columns=[stock_name]))
