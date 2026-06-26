import streamlit as st
import requests
import time

# =========================
# CONFIG
# =========================
st.set_page_config(layout="wide", page_title="三竹級看盤系統")

# =========================
# STATE CONTROL（避免閃爍核心）
# =========================
if "running" not in st.session_state:
    st.session_state.running = False

if "refresh" not in st.session_state:
    st.session_state.refresh = 2

# =========================
# STYLE
# =========================
st.markdown("""
<style>

body {
    background: #0b0f14;
    color: white;
}

/* CARD */
.card {
    background: #111823;
    border-radius: 14px;
    padding: 14px;
    border: 1px solid #1f2a3a;
    margin-bottom: 10px;
}

/* PRICE */
.price-up { color: #e74c3c; }
.price-down { color: #2ecc71; }

/* SIDEBAR STATUS */
.status-on { color: #2ecc71; font-weight: 700; }
.status-off { color: #888; }

.row {
    display: flex;
    justify-content: space-between;
    padding: 3px 0;
}

.buy { color: #2ecc71; }
.sell { color: #ff4d4d; }

.title {
    font-size: 22px;
    font-weight: 800;
}

.big {
    font-size: 52px;
    font-weight: 900;
}

</style>
""", unsafe_allow_html=True)

# =========================
# API
# =========================
def get_data(symbol, key):
    url = f"https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/{symbol}"
    headers = {"X-API-KEY": key}
    return requests.get(url, headers=headers).json()

# =========================
# SIDEBAR（控制台）
# =========================
st.sidebar.title("⚙️ 控制台")

key = st.sidebar.text_input("API Key", type="password")
symbol = st.sidebar.text_input("股票代碼", "2330")

refresh = st.sidebar.slider("更新頻率(秒)", 1, 10, 2)
st.session_state.refresh = refresh

colA, colB = st.sidebar.columns(2)

if colA.button("▶ 開始"):
    st.session_state.running = True

if colB.button("⛔ 停止"):
    st.session_state.running = False

st.sidebar.markdown("---")
st.sidebar.write(f"⏱ 更新：{st.session_state.refresh} 秒")
st.sidebar.write(f"狀態：{'ON' if st.session_state.running else 'OFF'}")

# =========================
# MAIN
# =========================
placeholder = st.empty()

def render(data):

    name = data.get("name", "N/A")
    price = data.get("lastPrice", 0)
    change = data.get("change", 0)
    pct = data.get("changePercent", 0)

    up = change >= 0
    color = "price-up" if up else "price-down"

    bids = data.get("bids", [])
    asks = data.get("asks", [])
    total = data.get("total", {})

    # ===== HEADER =====
    st.markdown(f"""
    <div class="card">
        <div class="title">⚡ {name} {symbol}</div>
        <div class="big {color}">{price}</div>
        <div>漲跌 {change} / {pct:.2f}%</div>
    </div>
    """, unsafe_allow_html=True)

    # ===== ORDERBOOK =====
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🟢 買方")
        st.markdown('<div class="card">', unsafe_allow_html=True)
        for b in bids[:5]:
            st.markdown(f'<div class="row"><span>{b["price"]}</span><span class="buy">{b["size"]}</span></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown("### 🔴 賣方")
        st.markdown('<div class="card">', unsafe_allow_html=True)
        for a in asks[:5]:
            st.markdown(f'<div class="row"><span class="sell">{a["size"]}</span><span>{a["price"]}</span></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ===== TRADE =====
    st.markdown("### 📦 成交資訊")

    c1, c2, c3 = st.columns(3)

    c1.markdown(f"""<div class="card">成交金額<br><b>{total.get('tradeValue', 0):,}</b></div>""", unsafe_allow_html=True)
    c2.markdown(f"""<div class="card">成交量<br><b>{total.get('tradeVolume', 0):,}</b></div>""", unsafe_allow_html=True)
    c3.markdown(f"""<div class="card">成交筆數<br><b>{total.get('transaction', 0):,}</b></div>""", unsafe_allow_html=True)

# =========================
# LOOP（重點：避免閃爍）
# =========================
while True:

    if not st.session_state.running:
        st.info("請按左側 ▶ 開始")
        time.sleep(1)
        continue

    if not key:
        st.warning("請輸入 API KEY")
        time.sleep(1)
        continue

    data = get_data(symbol, key)

    with placeholder.container():
        render(data)

    time.sleep(st.session_state.refresh)
