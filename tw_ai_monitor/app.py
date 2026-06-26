import streamlit as st
import requests
import time

# =========================
# CONFIG
# =========================
st.set_page_config(layout="wide", page_title="AI 當沖判斷系統")

# =========================
# API
# =========================
def get_data(symbol, key):
    url = f"https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/{symbol}"
    return requests.get(url, headers={"X-API-KEY": key}).json()

# =========================
# AI TRADING ENGINE（核心🔥）
# =========================
def ai_signal(data):

    bids = data.get("bids", [])
    asks = data.get("asks", [])

    bid_vol = sum([b["size"] for b in bids[:5]])
    ask_vol = sum([a["size"] for a in asks[:5]])

    price = data.get("lastPrice", 0)
    change = data.get("change", 0)

    # 1️⃣ 盤口力道
    imbalance = bid_vol / (ask_vol + 1)

    # 2️⃣ 趨勢
    trend = 1 if change > 0 else -1

    # 3️⃣ AI rule scoring
    score = 50

    if imbalance > 1.2:
        score += 20
    elif imbalance < 0.8:
        score -= 20

    score += trend * 10

    # 4️⃣ decision
    if score >= 65:
        return "📈 做多 (LONG)", score
    elif score <= 35:
        return "📉 做空 (SHORT)", score
    else:
        return "⏸ 觀望 (HOLD)", score

# =========================
# UI
# =========================
st.title("🧠 AI 當沖多空判斷（Real Market Data）")

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

    signal, score = ai_signal(data)

    price = data.get("lastPrice", 0)

    with placeholder.container():

        st.markdown(f"## {symbol} 即時 AI 判斷")

        st.markdown(f"### 價格：{price}")

        st.markdown(f"## AI 判斷結果：{signal}")

        st.markdown(f"### 信心分數：{score}/100")

        st.progress(score / 100)

        st.write("---")

        st.write("買盤力道", sum([b["size"] for b in data.get("bids", [])[:5]]))
        st.write("賣盤力道", sum([a["size"] for a in data.get("asks", [])[:5]]))

    time.sleep(refresh)
