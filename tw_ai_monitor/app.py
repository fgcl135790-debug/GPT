import streamlit as st
import requests
import time
from datetime import datetime

# ======================
# Page Config
# ======================
st.set_page_config(page_title="TW Stock Monitor", layout="wide")

# ======================
# CSS (dark + mi-trade style)
# ======================
st.markdown("""
<style>
body {
    background-color: #0e1117;
}

/* card */
.card {
    background: #121212;
    padding: 18px;
    border-radius: 12px;
}

/* price up/down */
.up {
    color: #ff3b3b; /* 台股：漲紅 */
    font-weight: 700;
}

.down {
    color: #00c853; /* 台股：跌綠 */
    font-weight: 700;
}

.gray {
    color: #aaa;
}

/* sidebar */
section[data-testid="stSidebar"] {
    background-color: #111318;
}
</style>
""", unsafe_allow_html=True)

# ======================
# Sidebar Control Panel
# ======================
st.sidebar.title("⚙️ 控制台")

api_key = st.sidebar.text_input("Fugle API Key", type="password")
symbol = st.sidebar.text_input("股票代碼", value="2330")

refresh_sec = st.sidebar.slider("更新頻率（秒）", 1, 10, 2)

st.sidebar.markdown("---")
status_box = st.sidebar.empty()

start = st.sidebar.button("開始更新")
stop = st.sidebar.button("停止更新")

# session state
if "running" not in st.session_state:
    st.session_state.running = False

if start:
    st.session_state.running = True

if stop:
    st.session_state.running = False

status_box.markdown(f"**狀態：** {'ON' if st.session_state.running else 'OFF'}")
st.sidebar.markdown(f"⏱️ 目前更新頻率：**{refresh_sec} 秒**")

# ======================
# API
# ======================
def get_quote(symbol, api_key):
    url = f"https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/{symbol}"
    headers = {"X-API-KEY": api_key}
    r = requests.get(url, headers=headers)
    return r.json()

# ======================
# UI containers (避免閃爍)
# ======================
quote_box = st.empty()
order_box = st.empty()
info_box = st.empty()

# ======================
# main loop
# ======================
if st.session_state.running:

    while True:

        if not st.session_state.running:
            break

        data = get_quote(symbol, api_key)

        name = data.get("name", symbol)
        price = data.get("lastPrice", 0)
        change = data.get("change", 0)
        change_pct = data.get("changePercent", 0)

        color_class = "up" if change > 0 else "down"

        # ======================
        # Top quote
        # ======================
        quote_box.markdown(f"""
        <div class="card">
            <div style="font-size:18px; color:#ccc;">⚡ {name} ({symbol})</div>

            <div style="font-size:48px; font-weight:800;" class="{color_class}">
                {price}
            </div>

            <div class="gray">
                漲跌：{change} / {change_pct:.2f}%
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ======================
        # 五檔
        # ======================
        bids = data.get("bids", [])
        asks = data.get("asks", [])

        bid_html = ""
        ask_html = ""

        for b in bids:
            bid_html += f"<div>{b['price']} ｜ <span class='up'>{b['size']}</span></div>"

        for a in asks:
            ask_html += f"<div><span class='down'>{a['size']}</span> ｜ {a['price']}</div>"

        order_box.markdown(f"""
        <div style="display:flex; gap:80px;">

            <div>
                <h3>🟢 買方</h3>
                {bid_html}
            </div>

            <div>
                <h3>🔴 賣方</h3>
                {ask_html}
            </div>

        </div>
        """, unsafe_allow_html=True)

        # ======================
        # 成交資訊
        # ======================
        total = data.get("total", {})

        trade_value = total.get("tradeValue", 0)
        trade_volume = total.get("tradeVolume", 0)
        transaction = total.get("transaction", 0)

        info_box.markdown(f"""
        <div class="card">
            <h3>📦 成交資訊</h3>

            <div style="display:flex; gap:80px;">
                <div>
                    成交金額<br>
                    <b>{trade_value:,}</b>
                </div>

                <div>
                    成交張數<br>
                    <b>{trade_volume:,}</b>
                </div>

                <div>
                    成交筆數<br>
                    <b>{transaction:,}</b>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        time.sleep(refresh_sec)

else:
    st.info("請按左側「開始更新」")
