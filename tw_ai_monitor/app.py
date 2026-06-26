import streamlit as st
import requests
import time
import numpy as np

# =========================
# CONFIG
# =========================
st.set_page_config(layout="wide", page_title="法人級看盤系統")

# =========================
# STATE
# =========================
if "run" not in st.session_state:
    st.session_state.run = False

if "refresh" not in st.session_state:
    st.session_state.refresh = 2

# =========================
# STYLE
# =========================
st.markdown("""
<style>

body { background:#0b0f14; color:white; }

.card {
    background:#111823;
    padding:14px;
    border-radius:14px;
    border:1px solid #1f2a3a;
    margin-bottom:10px;
}

.title { font-size:22px; font-weight:800; }
.big { font-size:52px; font-weight:900; }

.up { color:#e74c3c; }
.down { color:#2ecc71; }

.buy { color:#2ecc71; }
.sell { color:#ff4d4d; }

.row { display:flex; justify-content:space-between; padding:3px 0; }

.badge {
    padding:4px 10px;
    border-radius:10px;
    font-size:12px;
    display:inline-block;
}

.accumulation { background:#1e3d2f; color:#2ecc71; }
.distribution { background:#3d1e1e; color:#ff4d4d; }
.sideways { background:#2a2a2a; color:#ccc; }

</style>
""", unsafe_allow_html=True)

# =========================
# API
# =========================
def get_data(symbol, key):
    url = f"https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/{symbol}"
    return requests.get(url, headers={"X-API-KEY": key}).json()

# =========================
# CONTROL PANEL
# =========================
st.sidebar.title("⚙️ 法人控制台")

key = st.sidebar.text_input("API Key", type="password")
symbol = st.sidebar.text_input("股票代碼", "2330")

refresh = st.sidebar.slider("更新頻率", 1, 10, 2)
st.session_state.refresh = refresh

if st.sidebar.button("▶ 開始"):
    st.session_state.run = True

if st.sidebar.button("⛔ 停止"):
    st.session_state.run = False

st.sidebar.write(f"狀態：{'ON' if st.session_state.run else 'OFF'}")

# =========================
# CORE ANALYTICS ENGINE (法人核心🔥)
# =========================
def compute_institution_signal(bids, asks):

    bid_vol = sum([b["size"] for b in bids[:5]])
    ask_vol = sum([a["size"] for a in asks[:5]])

    ratio = bid_vol / (ask_vol + 1)

    if ratio > 1.2:
        return "accumulation", ratio
    elif ratio < 0.8:
        return "distribution", ratio
    else:
        return "sideways", ratio


def detect_big_money(bids, asks):
    big_orders = []

    for b in bids:
        if b["size"] > 800:
            big_orders.append(("BUY", b["price"], b["size"]))

    for a in asks:
        if a["size"] > 800:
            big_orders.append(("SELL", a["price"], a["size"]))

    return big_orders


def trend_score(data):
    price = data.get("lastPrice", 0)
    change = data.get("change", 0)
    vol = data.get("total", {}).get("tradeVolume", 1)

    score = 50

    if change > 0:
        score += 10
    else:
        score -= 10

    if vol > 20000:
        score += 15

    return max(0, min(100, score))

# =========================
# RENDER
# =========================
placeholder = st.empty()

while True:

    if not st.session_state.run:
        st.info("等待開始...")
        time.sleep(1)
        continue

    if not key:
        st.warning("請輸入 API KEY")
        time.sleep(1)
        continue

    data = get_data(symbol, key)

    name = data.get("name", symbol)
    price = data.get("lastPrice", 0)
    change = data.get("change", 0)
    pct = data.get("changePercent", 0)

    bids = data.get("bids", [])
    asks = data.get("asks", [])
    total = data.get("total", {})

    signal, ratio = compute_institution_signal(bids, asks)
    big_orders = detect_big_money(bids, asks)
    score = trend_score(data)

    with placeholder.container():

        # ================= HEADER =================
        st.markdown(f"""
        <div class="card">
            <div class="title">🏦 法人級看盤｜{name} {symbol}</div>
            <div class="big">{price}</div>
            <div>漲跌 {change} / {pct:.2f}%</div>
        </div>
        """, unsafe_allow_html=True)

        # ================= SIGNAL =================
        st.markdown("### 🧠 法人訊號")

        st.markdown(f"""
        <div class="card">
            <span class="badge {signal}">
                {signal.upper()}
            </span>
            <br><br>
            籌碼比率：{ratio:.2f}<br>
            趨勢分數：{score}/100
        </div>
        """, unsafe_allow_html=True)

        # ================= BIG MONEY =================
        st.markdown("### 💰 大單偵測")

        st.markdown('<div class="card">', unsafe_allow_html=True)
        if big_orders:
            for side, p, s in big_orders:
                st.markdown(f"{side}｜{p}｜{s}")
        else:
            st.write("無異常大單")
        st.markdown('</div>', unsafe_allow_html=True)

        # ================= ORDERBOOK =================
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 🟢 買盤")
            st.markdown('<div class="card">', unsafe_allow_html=True)
            for b in bids[:5]:
                st.markdown(f'<div class="row"><span>{b["price"]}</span><span class="buy">{b["size"]}</span></div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with col2:
            st.markdown("### 🔴 賣盤")
            st.markdown('<div class="card">', unsafe_allow_html=True)
            for a in asks[:5]:
                st.markdown(f'<div class="row"><span class="sell">{a["size"]}</span><span>{a["price"]}</span></div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # ================= SUMMARY =================
        st.markdown("### 📦 成交資訊")

        c1, c2, c3 = st.columns(3)

        c1.markdown(f"<div class='card'>成交金額<br><b>{total.get('tradeValue',0):,}</b></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='card'>成交量<br><b>{total.get('tradeVolume',0):,}</b></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='card'>成交筆數<br><b>{total.get('transaction',0):,}</b></div>", unsafe_allow_html=True)

    time.sleep(st.session_state.refresh)
