import streamlit as st
import requests
import time

# =========================
# CONFIG
# =========================
st.set_page_config(layout="wide", page_title="AI 實戰交易系統")

# =========================
# STATE
# =========================
if "running" not in st.session_state:
    st.session_state.running = False

if "trade_count" not in st.session_state:
    st.session_state.trade_count = 0

if "loss_streak" not in st.session_state:
    st.session_state.loss_streak = 0

# =========================
# API
# =========================
def get_data(symbol, key):
    url = f"https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/{symbol}"
    return requests.get(url, headers={"X-API-KEY": key}).json()

# =========================
# INDICATORS
# =========================
def calc_vwap(data):
    bids = data.get("bids", [])
    asks = data.get("asks", [])

    vol = 0
    val = 0

    for b in bids:
        vol += b["size"]
        val += b["size"] * b["price"]

    for a in asks:
        vol += a["size"]
        val += a["size"] * a["price"]

    return val / vol if vol > 0 else data.get("lastPrice", 0)

def order_imbalance(data):
    bids = data.get("bids", [])
    asks = data.get("asks", [])

    bid = sum([b["size"] for b in bids[:5]])
    ask = sum([a["size"] for a in asks[:5]])

    return bid / (ask + 1)

# =========================
# AI SIGNAL ENGINE
# =========================
def ai_engine(data):

    price = data["lastPrice"]
    change = data["change"]
    vwap = calc_vwap(data)
    imb = order_imbalance(data)

    score = 50

    # trend
    if change > 0:
        score += 10
    else:
        score -= 10

    # vwap bias
    if price > vwap:
        score += 10
    else:
        score -= 10

    # pressure
    if imb > 1.2:
        score += 20
    elif imb < 0.8:
        score -= 20

    # ================= decision =================
    if score >= 80:
        return "🔥 強力做多", score, vwap
    elif score >= 65:
        return "📈 可做多", score, vwap
    elif score >= 40:
        return "⏸ 觀望", score, vwap
    else:
        return "📉 做空 / 避免多單", score, vwap

# =========================
# RISK ENGINE (重點🔥)
# =========================
def risk_check(score):

    if st.session_state.loss_streak >= 3:
        return False, "❌ 連續虧損，停止交易"

    if score > 85:
        return True, "✅ 高勝率區"

    if score < 35:
        return False, "❌ 低品質訊號"

    return True, "⚠️ 一般訊號"

# =========================
# UI
# =========================
st.title("🧠 AI 實戰交易系統（可用版）")

key = st.text_input("API KEY", type="password")
symbol = st.text_input("股票代碼", "2330")

refresh = st.slider("更新秒數", 1, 10, 2)

if st.button("開始"):
    st.session_state.running = True

if st.button("停止"):
    st.session_state.running = False

placeholder = st.empty()

# =========================
# LOOP
# =========================
while st.session_state.running:

    if not key:
        st.warning("請輸入 API KEY")
        break

    data = get_data(symbol, key)

    signal, score, vwap = ai_engine(data)
    ok, risk_msg = risk_check(score)

    price = data["lastPrice"]

    # =========================
    # SIM TRADE LOGIC (實戰邏輯)
    # =========================
    if ok and score >= 65:
        st.session_state.trade_count += 1

    with placeholder.container():

        st.markdown(f"## {symbol} AI 實戰交易")

        st.metric("價格", price)
        st.metric("VWAP", round(vwap, 2))

        st.markdown(f"## 訊號：{signal}")
        st.markdown(f"### Score：{score}")

        st.progress(score / 100)

        st.markdown(f"### 風控狀態：{risk_msg}")

        st.markdown("---")
        st.write("交易次數：", st.session_state.trade_count)
        st.write("連續虧損：", st.session_state.loss_streak)

    time.sleep(refresh)
