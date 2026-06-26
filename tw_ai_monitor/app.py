import streamlit as st
import requests
import time

# ======================
# PAGE CONFIG
# ======================
st.set_page_config(page_title="台股看盤系統", layout="wide")

# ======================
# STYLE (仿你圖片 dark dashboard)
# ======================
st.markdown("""
<style>

body {
    background-color: #0b0f14;
}

.big-price {
    font-size: 56px;
    font-weight: 800;
}

.up { color: #e74c3c; }   /* 台股：漲紅 */
.down { color: #2ecc71; } /* 台股：跌綠 */

.card {
    background: #111823;
    padding: 16px;
    border-radius: 14px;
    border: 1px solid #1f2a3a;
}

.title {
    font-size: 22px;
    font-weight: 700;
}

.sub {
    color: #aaa;
    font-size: 13px;
}

.section-title {
    margin-top: 20px;
    font-size: 18px;
    font-weight: 700;
    color: #ddd;
}

.table-row {
    display: flex;
    justify-content: space-between;
    padding: 4px 0;
}

.buy { color: #2ecc71; }
.sell { color: #ff4d4d; }

.small {
    font-size: 13px;
    color: #bbb;
}

hr {
    border: 0;
    border-top: 1px solid #222;
}

</style>
""", unsafe_allow_html=True)

# ======================
# API
# ======================
def get_data(symbol, key):
    url = f"https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/{symbol}"
    headers = {"X-API-KEY": key}
    r = requests.get(url, headers=headers)
    return r.json()

# ======================
# SIDEBAR (控制台)
# ======================
st.sidebar.title("⚙️ 控制台")

api_key = st.sidebar.text_input("Fugle API Key", type="password")
symbol = st.sidebar.text_input("股票代碼", "2330")

refresh_sec = st.sidebar.slider("更新頻率（秒）", 1, 10, 2)

start = st.sidebar.button("開始")
stop = st.sidebar.button("停止")

if "run" not in st.session_state:
    st.session_state.run = False

if start:
    st.session_state.run = True
if stop:
    st.session_state.run = False

st.sidebar.markdown("---")
st.sidebar.write(f"⏱ 更新頻率：{refresh_sec} 秒")
st.sidebar.write(f"狀態：{'ON' if st.session_state.run else 'OFF'}")

# ======================
# MAIN
# ======================
placeholder = st.empty()

while st.session_state.run:

    if not api_key:
        st.warning("請輸入 API KEY")
        break

    data = get_data(symbol, api_key)

    name = data.get("name", symbol)
    price = data.get("lastPrice", 0)
    change = data.get("change", 0)
    pct = data.get("changePercent", 0)

    is_up = change >= 0
    color = "up" if is_up else "down"

    bids = data.get("bids", [])
    asks = data.get("asks", [])
    total = data.get("total", {})

    with placeholder.container():

        # ================= HEADER =================
        st.markdown(f"""
        <div class="card">
            <div class="title">⚡ {name} {symbol}</div>
            <div class="big-price {color}">{price}</div>
            <div class="sub">漲跌：{change} / {pct:.2f}%</div>
        </div>
        """, unsafe_allow_html=True)

        st.write("")

        # ================= FIVE LEVEL =================
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 🟢 買方")
            st.markdown("<div class='card'>", unsafe_allow_html=True)

            st.markdown("價格 | 張數")
            for b in bids[:5]:
                st.markdown(f"<div class='table-row'><span>{b['price']}</span><span class='buy'>{b['size']}</span></div>", unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)

        with col2:
            st.markdown("### 🔴 賣方")
            st.markdown("<div class='card'>", unsafe_allow_html=True)

            st.markdown("張數 | 價格")
            for a in asks[:5]:
                st.markdown(f"<div class='table-row'><span class='sell'>{a['size']}</span><span>{a['price']}</span></div>", unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)

        # ================= TOTAL =================
        st.markdown("### 📦 成交資訊")

        c1, c2, c3 = st.columns(3)

        c1.markdown(f"<div class='card'>成交金額<br><b>{total.get('tradeValue', 0):,}</b></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='card'>成交量<br><b>{total.get('tradeVolume', 0):,}</b></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='card'>成交筆數<br><b>{total.get('transaction', 0):,}</b></div>", unsafe_allow_html=True)

    time.sleep(refresh_sec)
