import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="AI 當沖 V8.1", layout="wide")

# =========================
# SIDEBAR
# =========================
st.sidebar.title("⚙️ 控制台")

api_key = st.sidebar.text_input("API KEY", type="password")
stock = st.sidebar.text_input("股票代碼", "2330")
refresh = st.sidebar.slider("更新頻率(秒)", 1, 10, 2)

# =========================
# 🧠 股票名稱 mapping（可擴充）
# =========================
stock_name_map = {
    "2330": "台積電",
    "2317": "鴻海",
    "2454": "聯發科",
    "2313": "華通",
    "3481": "群創"
}

stock_name = stock_name_map.get(stock, stock)

# =========================
# 🚨 換股票 → 清空 chart
# =========================
if "last_stock" not in st.session_state:
    st.session_state.last_stock = stock

if st.session_state.last_stock != stock:
    st.session_state.hist = []   # 🔥 清空走勢圖
    st.session_state.last_stock = stock

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
        "change": d.get("change", 0),
        "bids": d.get("bids", []),
        "asks": d.get("asks", [])
    }

# =========================
# ENGINE
# =========================
def engine(d):
    price = d["price"]
    vwap = d["vwap"]

    bid = sum(x.get("size", 0) for x in d["bids"][:3])
    ask = sum(x.get("size", 0) for x in d["asks"][:3])

    imbalance = (bid - ask) / max(1, bid + ask)

    long = price > vwap and imbalance > 0.1
    short = price < vwap and imbalance < -0.1

    if long:
        return "📈 多方進場", "站上VWAP + 買盤優勢"
    elif short:
        return "📉 空方進場", "跌破VWAP + 賣壓主導"
    else:
        return "⚖️ 觀望", "多空平衡"

# =========================
# UI TITLE（改成股名）
# =========================
st.title(f"⚡ {stock_name} AI 當沖 V8.1")

if not api_key:
    st.warning("請輸入 API KEY")
    st.stop()

d = get_quote(stock, api_key)

# =========================
# METRICS
# =========================
col1, col2, col3, col4 = st.columns(4)

col1.metric("現價", d["price"])
col2.metric("VWAP", d["vwap"])
col3.metric("高點", d["high"])
col4.metric("低點", d["low"])

# =========================
# SIGNAL
# =========================
signal, reason = engine(d)

st.markdown("## 🤖 AI 當沖判斷")
st.success(signal)
st.write("📌", reason)

# =========================
# CHART (重點修正)
# =========================
if "hist" not in st.session_state:
    st.session_state.hist = []

st.session_state.hist.append(d["price"])

if len(st.session_state.hist) > 60:
    st.session_state.hist.pop(0)

st.markdown("## 📊 分時走勢")

st.line_chart(
    pd.DataFrame(st.session_state.hist, columns=[stock_name])
)
