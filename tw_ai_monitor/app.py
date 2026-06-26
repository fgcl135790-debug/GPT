import streamlit as st
import requests
import pandas as pd
from collections import deque

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="V9 Trading System", layout="wide")

# =========================
# SIDEBAR
# =========================
st.sidebar.title("⚙️ 控制台")

api_key = st.sidebar.text_input("API KEY", type="password")
stock = st.sidebar.text_input("股票代碼", "2330")
refresh = st.sidebar.slider("更新頻率(秒)", 1, 10, 2)
show_debug = st.sidebar.checkbox("Debug Mode", False)

# =========================
# STATE RESET (換股票就清空)
# =========================
if "last_stock" not in st.session_state:
    st.session_state.last_stock = stock

if st.session_state.last_stock != stock:
    st.session_state.hist = deque(maxlen=100)
    st.session_state.last_stock = stock

if "hist" not in st.session_state:
    st.session_state.hist = deque(maxlen=100)

# =========================
# API CALL（Fugle）
# =========================
def get_quote(stock, api_key):
    url = f"https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/{stock}"
    r = requests.get(url, headers={"X-API-KEY": api_key})

    try:
        d = r.json()
    except:
        return None

    if not d:
        return None

    return d

# =========================
# NORMALIZE DATA
# =========================
def normalize(d):
    return {
        "name": d.get("name", ""),
        "price": d.get("lastPrice") or d.get("closePrice") or 0,
        "vwap": d.get("avgPrice") or 0,
        "high": d.get("highPrice") or 0,
        "low": d.get("lowPrice") or 0,
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
# 反彈判斷
# =========================
def detect_rebound(price, low, vwap):
    if price <= low * 1.01:
        return "⚠️ 可能反彈區（接近低點）"
    if price < vwap and price > low:
        return "🟡 弱勢反彈可能"
    return "無反彈訊號"

# =========================
# 信心指數
# =========================
def confidence(score_parts):
    return int(sum(score_parts) / len(score_parts) * 100)

# =========================
# V9 ENGINE
# =========================
def v9_engine(d):
    price = d["price"]
    vwap = d["vwap"]
    high = d["high"]
    low = d["low"]

    imb, big_buy, big_sell = detect_institution(d)

    score = []

    # 多頭條件
    if price > vwap:
        score.append(0.7)
    else:
        score.append(0.3)

    score.append((imb + 1) / 2)

    if big_buy:
        score.append(0.8)
    else:
        score.append(0.4)

    conf = confidence(score)

    if price > vwap and imb > 0.15 and big_buy:
        signal = "📈 主力進場（多方）"
        reason = "VWAP上 + 買盤 + 大單進場"
        stop = vwap
        tp = high

    elif price < vwap and imb < -0.15 and big_sell:
        signal = "📉 主力出貨（空方）"
        reason = "VWAP下 + 賣壓 + 大單出貨"
        stop = vwap
        tp = low

    elif big_buy:
        signal = "⚠️ 主力吸籌"
        reason = "大單買進"
        stop = low
        tp = high

    else:
        signal = "⛔ 無明確訊號"
        reason = "盤整"
        stop = None
        tp = None

    return signal, reason, stop, tp, imb, conf

# =========================
# RUN
# =========================
if not api_key:
    st.warning("請輸入 API KEY")
    st.stop()

raw = get_quote(stock, api_key)

if not raw:
    st.error("API 無回應")
    st.stop()

d = normalize(raw)

# hist (走勢)
st.session_state.hist.append(d["price"])

# =========================
# TITLE（只顯示股名）
# =========================
title = d["name"] if d["name"] else stock
st.title(f"⚡ {title}")

# =========================
# METRICS
# =========================
col1, col2, col3, col4 = st.columns(4)

col1.metric("現價", d["price"])
col2.metric("VWAP", d["vwap"])
col3.metric("高點", d["high"])
col4.metric("低點", d["low"])

# =========================
# V9
# =========================
signal, reason, stop, tp, imb, conf = v9_engine(d)

st.markdown("## 🤖 V9 主力交易訊號")
st.success(signal)
st.write("📌", reason)

st.metric("信心指數", f"{conf}/100")

# 反彈
reb = detect_rebound(d["price"], d["low"], d["vwap"])
st.write("🔄", reb)

# 停損停利
st.markdown("### 🛑 停損 / 停利")
st.write("停損:", stop)
st.write("停利:", tp)

# =========================
# 五檔（三竹風格）
# =========================
st.markdown("## 📊 五檔報價")

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
# 主力力道
# =========================
st.markdown("## 📈 主力力道")
st.progress(min(1.0, max(0.0, (imb + 1) / 2)))
st.write("Imbalance:", round(imb, 3))

# =========================
# DEBUG
# =========================
if show_debug:
    st.markdown("## 🧪 DEBUG RAW")
    st.json(raw)

# =========================
# CHART（換股自動清空）
# =========================
st.markdown("## 📉 即時走勢")

if len(st.session_state.hist) > 1:
    st.line_chart(pd.DataFrame(list(st.session_state.hist), columns=[title]))
else:
    st.write("等待資料...")
