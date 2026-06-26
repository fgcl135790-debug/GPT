import streamlit as st
import requests
import time
import json

st.set_page_config(page_title="TW AI Monitor v3", layout="wide")

# ========== STYLE（台股紅漲綠跌） ==========
st.markdown("""
<style>
.big-price { font-size: 42px; font-weight: 700; }
.up { color: #E74C3C; }   /* 紅 */
.down { color: #2ECC71; } /* 綠 */
.box {
    padding: 16px;
    border-radius: 12px;
    background-color: #111;
}
</style>
""", unsafe_allow_html=True)


# ========== SESSION STATE ==========
if "running" not in st.session_state:
    st.session_state.running = True

if "data" not in st.session_state:
    st.session_state.data = None


# ========== SIDEBAR ==========
with st.sidebar:
    st.title("⚙️ 控制台")

    api_key = st.text_input("Fugle API Key", type="password")

    symbol = st.text_input("股票代碼", value="2330")

    refresh_sec = st.slider("更新頻率（秒）", 1, 10, 2)

    st.divider()

    st.write("狀態")
    st.write("Auto Refresh：ON")

    if st.button("停止更新"):
        st.session_state.running = False

    if st.button("開始更新"):
        st.session_state.running = True


# ========== API ==========
def fetch(symbol, api_key):
    url = f"https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/{symbol}"
    headers = {"X-API-KEY": api_key}

    r = requests.get(url, headers=headers, timeout=10)
    return r.json()


# ========== UI ==========
st.title(f"📊 台股看盤系統 {symbol}")

placeholder = st.empty()


# ========== LOOP ==========
while st.session_state.running:

    if not api_key:
        st.warning("請輸入 API KEY")
        time.sleep(1)
        continue

    try:
        data = fetch(symbol, api_key)
        st.session_state.data = data

        price = data.get("lastPrice", 0)
        change = data.get("change", 0)
        change_pct = data.get("changePercent", 0)

        color_class = "up" if change >= 0 else "down"

        with placeholder.container():

            # ====== 價格 ======
            st.markdown(f"""
            <div class="box">
                <div style="font-size:24px;">{data.get('name','')}</div>
                <div class="big-price {color_class}">{price}</div>
                <div>漲跌：{change} / {change_pct}%</div>
            </div>
            """, unsafe_allow_html=True)

            col1, col2 = st.columns(2)

            with col1:
                st.subheader("📉 買方")
                for b in data.get("bids", [])[:5]:
                    st.write(f"{b['price']} | {b['size']}")

            with col2:
                st.subheader("📈 賣方")
                for a in data.get("asks", [])[:5]:
                    st.write(f"{a['price']} | {a['size']}")

            st.subheader("📦 成交量")
            st.write(data.get("total", {}))

    except Exception as e:
        st.error(f"API error: {e}")

    time.sleep(refresh_sec)
