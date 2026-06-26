import streamlit as st
import requests
import pandas as pd
import time

st.set_page_config(page_title="台股 AI V8 交易決策系統", layout="wide")

# =========================
# SIDEBAR
# =========================
st.sidebar.title("⚙️ 控制台")

api_key = st.sidebar.text_input("API KEY", type="password")
stock = st.sidebar.text_input("股票代碼", "2330")
refresh = st.sidebar.slider("更新頻率(秒)", 1, 10, 2)

st.sidebar.markdown("---")
st.sidebar.write("📡 更新頻率:", refresh, "秒")

# =========================
# API
# =========================
def get_quote(stock, api_key):
    url = f"https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/{stock}"
    r = requests.get(url, headers={"X-API-KEY": api_key})
    d = r.json()

    return {
        "name": d.get("name", stock),
        "price": d.get("closePrice") or d.get("lastPrice", 0),
        "vwap": d.get("avgPrice", 0),
        "high": d.get("highPrice", 0),
        "low": d.get("lowPrice", 0),
        "change": d.get("change", 0),
        "bids": d.get("bids", []),
        "asks": d.get("asks", [])
    }

# =========================
# V8 TRADING ENGINE
# =========================
def v8_engine(d):
    price = d["price"]
    vwap = d["vwap"]

    bid_vol = sum([x.get("size", 0) for x in d["bids"][:3]])
    ask_vol = sum([x.get("size", 0) for x in d["asks"][:3]])

    imbalance = (bid_vol - ask_vol) / max(1, (bid_vol + ask_vol))

    # ================= VWAP LOGIC =================
    vwap_long = price > vwap and imbalance > 0.1
    vwap_short = price < vwap and imbalance < -0.1

    # ================= BREAKOUT TRAP =================
    fake_break_high = price >= d["high"] and d["change"] < 0
    fake_break_low = price <= d["low"] and d["change"] > 0

    # ================= SIGNAL =================
    if vwap_long and not fake_break_high:
        signal = "📈 多方進場區"
        reason = "VWAP站上 + 買盤優勢"
        action = "回踩做多"
        stop = vwap

    elif vwap_short and not fake_break_low:
        signal = "📉 空方進場區"
        reason = "跌破VWAP + 賣壓主導"
        action = "反彈放空"
        stop = vwap

    else:
        signal = "⚖️ 觀望區"
        reason = "多空拉鋸 / 無明確趨勢"
        action = "等待訊號"
        stop = None

    # ================= FAKE BREAK WARNING =================
    if fake_break_high or fake_break_low:
        warning = "⚠️ 假突破警告（流動性陷阱可能）"
    else:
        warning = "✔ 無假突破"

    return signal, reason, action, stop, warning, imbalance

# =========================
# UI
# =========================
st.title(f"⚡ {stock} AI 當沖決策系統 V8")

if not api_key:
    st.warning("請輸入 API KEY")
    st.stop()

d = get_quote(stock, api_key)

# =========================
# TOP METRICS
# =========================
col1, col2, col3, col4 = st.columns(4)

col1.metric("現價", d["price"])
col2.metric("VWAP", d["vwap"])
col3.metric("高點", d["high"])
col4.metric("低點", d["low"])

# =========================
# ENGINE RESULT
# =========================
signal, reason, action, stop, warning, imbalance = v8_engine(d)

st.markdown("## 🤖 V8 交易決策")

st.success(signal)
st.write("📌 原因：", reason)
st.write("🎯 策略：", action)
st.write("🛑 停損：", stop)
st.warning(warning)

# =========================
# ORDER BOOK
# =========================
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
# IMBALANCE BAR
# =========================
st.markdown("## 📊 多空力道")

st.progress(min(1.0, max(0.0, (imbalance + 1) / 2)))
st.write("Order Book Imbalance:", round(imbalance, 3))

# =========================
# PRICE HISTORY
# =========================
if "hist" not in st.session_state:
    st.session_state.hist = []

st.session_state.hist.append(d["price"])

if len(st.session_state.hist) > 60:
    st.session_state.hist.pop(0)

st.line_chart(pd.DataFrame(st.session_state.hist, columns=["price"]))
