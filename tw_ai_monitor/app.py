import streamlit as st
import requests
import time

# ========== PAGE ==========
st.set_page_config(page_title="台股看盤", layout="wide")

# ========== STYLE ==========
st.markdown("""
<style>
.big-price { font-size: 54px; font-weight: 800; }
.up { color: #e74c3c; }   /* 台股：上漲紅 */
.down { color: #2ecc71; } /* 台股：下跌綠 */
.gray { color: #aaa; }
.box { padding: 16px; border-radius: 12px; background: #111; }
</style>
""", unsafe_allow_html=True)

# ========== API ==========
def get_quote(symbol, api_key):
    url = f"https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/{symbol}"
    headers = {"X-API-KEY": api_key}
    r = requests.get(url, headers=headers)
    return r.json()

# ========== SIDEBAR ==========
st.sidebar.title("⚙️ 控制台")

api_key = st.sidebar.text_input("Fugle API Key", type="password")
symbol = st.sidebar.text_input("股票代碼", "2330")

refresh_sec = st.sidebar.slider("更新頻率（秒）", 1, 10, 2)

start = st.sidebar.button("開始更新")
stop = st.sidebar.button("停止更新")

if "run" not in st.session_state:
    st.session_state.run = False

if start:
    st.session_state.run = True
if stop:
    st.session_state.run = False

st.sidebar.markdown("---")
st.sidebar.write(f"⏱ 目前更新頻率：{refresh_sec} 秒")
st.sidebar.write(f"狀態：{'ON' if st.session_state.run else 'OFF'}")

# ========== MAIN ==========
placeholder = st.empty()

while st.session_state.run:

    if not api_key:
        st.warning("請輸入 API Key")
        break

    data = get_quote(symbol, api_key)

    name = data.get("name", "")
    last = data.get("lastPrice", 0)
    change = data.get("change", 0)
    pct = data.get("changePercent", 0)

    is_up = change >= 0
    color_class = "up" if is_up else "down"

    bids = data.get("bids", [])
    asks = data.get("asks", [])

    total = data.get("total", {})

    with placeholder.container():

        # ===== HEADER =====
        st.title(f"⚡ {name} ({symbol})")

        st.markdown(f"""
        <div class="box">
            <div class="big-price {color_class}">{last}</div>
            <div class="gray">漲跌：{change} / {pct:.2f}%</div>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        # ===== BUY =====
        with col1:
            st.subheader("🟢 買方（BID）")
            for b in bids[:5]:
                st.write(f"{b['price']}  |  {b['size']}")

        # ===== SELL =====
        with col2:
            st.subheader("🔴 賣方（ASK）")
            for a in asks[:5]:
                st.write(f"{a['price']}  |  {a['size']}")

        # ===== TOTAL =====
        st.subheader("📦 成交資訊")

        c1, c2, c3 = st.columns(3)

        c1.metric("成交金額", f"{total.get('tradeValue', 0):,}")
        c2.metric("成交量", f"{total.get('tradeVolume', 0):,}")
        c3.metric("成交筆數", f"{total.get('transaction', 0):,}")

    time.sleep(refresh_sec)
