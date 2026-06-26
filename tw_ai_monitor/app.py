import streamlit as st
import requests
import time

# =========================
# CONFIG
# =========================
st.set_page_config(layout="wide", page_title="AI 當沖 2.0")

# =========================
# API
# =========================
def get_data(symbol, key):
    url = f"https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/{symbol}"
    return requests.get(url, headers={"X-API-KEY": key}).json()

# =========================
# VWAP CALC
# =========================
def calc_vwap(data):
    """
    用近似法（Fugle 沒 tick 就用 bid/ask proxy）
    """
    bids = data.get("bids", [])
    asks = data.get("asks", [])

    total_vol = 0
    total_val = 0

    for b in bids:
        total_vol += b["size"]
        total_val += b["price"] * b["size"]

    for a in asks:
        total_vol += a["size"]
        total_val += a["price"] * a["size"]

    if total_vol == 0:
        return data.get("lastPrice", 0)

    return total_val / total_vol

# =========================
# FALSE BREAKOUT DETECTOR
# =========================
def fake_breakout(data, vwap):

    price = data.get("lastPrice", 0)
    change = data.get("change", 0)

    bids = data.get("bids", [])
    asks = data.get("asks", [])

    bid_vol = sum([b["size"] for b in bids[:5]])
    ask_vol = sum([a["size"] for a in asks[:5]])

    imbalance = bid_vol / (ask_vol + 1)

    # 🔥 假突破邏輯
    if price > vwap and imbalance < 0.9:
        return True, "上漲假突破"
    if price < vwap and imbalance > 1.1:
        return True, "下跌假突破"

    # 無明顯假突破
    return False, None

# =========================
# AI ENGINE 2.0
# =========================
def ai_v2(data):

    price = data.get("lastPrice", 0)
    change = data.get("change", 0)

    vwap = calc_vwap(data)

    fake, reason = fake_breakout(data, vwap)

    bids = data.get("bids", [])
    asks = data.get("asks", [])

    bid_vol = sum([b["size"] for b in bids[:5]])
    ask_vol = sum([a["size"] for a in asks[:5]])

    imbalance = bid_vol / (ask_vol + 1)

    score = 50

    # 1️⃣ VWAP bias
    if price > vwap:
        score += 10
    else:
        score -= 10

    # 2️⃣ orderbook pressure
    if imbalance > 1.2:
        score += 15
    elif imbalance < 0.8:
        score -= 15

    # 3️⃣ momentum
    if change > 0:
        score += 10
    else:
        score -= 10

    # 4️⃣ fake breakout penalty (重點🔥)
    if fake:
        score = 20  # 強制降級

    # ================= decision =================
    if fake:
        return "⚠️ 假突破（禁止進場）", score, vwap, reason

    if score >= 65:
        return "📈 做多（強）", score, vwap, None
    elif score <= 35:
        return "📉 做空（強）", score, vwap, None
    else:
        return "⏸ 觀望", score, vwap, None

# =========================
# UI
# =========================
st.title("🧠 AI 當沖 2.0（VWAP + 假突破）")

key = st.text_input("API KEY", type="password")
symbol = st.text_input("股票代碼", "2330")

refresh = st.slider("更新秒數", 1, 10, 2)

run = st.button("開始")

placeholder = st.empty()

# =========================
# LOOP
# =========================
while run:

    if not key:
        st.warning("請輸入 API KEY")
        break

    data = get_data(symbol, key)

    signal, score, vwap, reason = ai_v2(data)

    price = data.get("lastPrice", 0)

    with placeholder.container():

        st.markdown(f"## {symbol} AI 當沖 2.0")

        st.markdown(f"### 價格：{price}")
        st.markdown(f"### VWAP：{round(vwap,2)}")

        st.markdown(f"## AI 判斷：{signal}")
        st.markdown(f"### 信心分數：{score}/100")

        st.progress(score / 100)

        if reason:
            st.error(f"偵測：{reason}")

        st.write("---")
        st.write("買盤壓力", sum([b["size"] for b in data.get("bids", [])[:5]]))
        st.write("賣盤壓力", sum([a["size"] for a in data.get("asks", [])[:5]]))

    time.sleep(refresh)
