import streamlit as st
import requests
import time

# =========================
# Page Config
# =========================
st.set_page_config(
    page_title="TW Quote System",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================
# Session State
# =========================
if "running" not in st.session_state:
    st.session_state.running = True

if "data" not in st.session_state:
    st.session_state.data = None

# =========================
# Sidebar (控制台)
# =========================
st.sidebar.title("⚙️ 控制台")

api_key = st.sidebar.text_input("Fugle API Key", type="password")
symbol = st.sidebar.text_input("股票代碼", value="2330")

refresh_sec = st.sidebar.slider("更新頻率（秒）", 1, 10, 2)

col1, col2 = st.sidebar.columns(2)
with col1:
    if st.button("停止更新"):
        st.session_state.running = False
with col2:
    if st.button("開始更新"):
        st.session_state.running = True

st.sidebar.markdown("---")
st.sidebar.write(f"Auto Refresh: {'ON' if st.session_state.running else 'OFF'}")

# =========================
# API
# =========================
def fetch_quote():
    url = f"https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/{symbol}"
    headers = {"X-API-KEY": api_key.strip()}

    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            return res.json()
        return None
    except:
        return None

# =========================
# 台股顏色（重點修正）
# =========================
def tw_color(change):
    return "#e53935" if change < 0 else "#00c853"

def tw_arrow(change):
    return "📉 下跌" if change < 0 else "📈 上漲"

# =========================
# Layout
# =========================
placeholder = st.empty()

# =========================
# Main Loop
# =========================
while True:

    if not st.session_state.running:
        time.sleep(0.5)
        continue

    data = fetch_quote()
    if not data:
        st.warning("API 無資料或 KEY 錯誤")
        time.sleep(refresh_sec)
        continue

    price = data["lastPrice"]
    change = data["change"]
    pct = data["changePercent"]

    bids = data["bids"]
    asks = data["asks"]

    # =========================
    # Render
    # =========================
    with placeholder.container():

        st.markdown(f"## 📊 台股看盤系統 {symbol}")

        # ===== Price =====
        st.markdown(
            f"""
            <div style="padding:20px;border-radius:10px;background:#111">
                <h2 style="color:{tw_color(change)}">{price}</h2>
                <p>{tw_arrow(change)}　{change} / {pct:.2f}%</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.write("")

        # =========================
        # 五檔（仿三竹）
        # =========================
        colL, colR = st.columns(2)

        with colL:
            st.markdown("### 🟢 買方")
            st.markdown("**價格　　張數**")

            for b in bids:
                st.markdown(
                    f"<span style='color:#00c853'>{b['price']}　　{b['size']}</span>",
                    unsafe_allow_html=True
                )

        with colR:
            st.markdown("### 🔴 賣方")
            st.markdown("**張數　　價格**")

            for a in asks:
                st.markdown(
                    f"<span style='color:#e53935'>{a['size']}　　{a['price']}</span>",
                    unsafe_allow_html=True
                )

        # =========================
        # 成交資訊（整理版）
        # =========================
        st.markdown("### 📦 成交資訊")

        total = data["total"]

        c1, c2, c3 = st.columns(3)

        c1.metric("成交金額", f"{total['tradeValue']:,}")
        c2.metric("成交張數", f"{total['tradeVolume']:,}")
        c3.metric("成交筆數", f"{total['transaction']:,}")

    time.sleep(refresh_sec)
