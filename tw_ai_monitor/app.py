import streamlit as st
import time
import random
from datetime import datetime

# =========================
# Page Config
# =========================
st.set_page_config(
    page_title="券商交易室看盤系統",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================
# Session State
# =========================
if "running" not in st.session_state:
    st.session_state.running = False

if "refresh_rate" not in st.session_state:
    st.session_state.refresh_rate = 2

if "last_update" not in st.session_state:
    st.session_state.last_update = time.time()

# =========================
# Fake Data (可換 API)
# =========================
def get_price_data():
    base = 2340 + random.randint(-5, 5)
    change = random.randint(-50, 50)
    pct = round(change / base * 100, 2)

    bids = [
        (2335, random.randint(300, 900)),
        (2330, random.randint(800, 1500)),
        (2325, random.randint(300, 1200)),
        (2320, random.randint(300, 900)),
        (2315, random.randint(200, 800)),
    ]

    asks = [
        (2340, random.randint(300, 900)),
        (2345, random.randint(300, 900)),
        (2350, random.randint(300, 900)),
        (2355, random.randint(300, 900)),
        (2360, random.randint(300, 900)),
    ]

    return {
        "name": "台積電",
        "code": "2330",
        "price": base,
        "change": change,
        "pct": pct,
        "bids": bids,
        "asks": asks,
        "amount": random.randint(80_000_000_000, 120_000_000_000),
        "volume": random.randint(30_000, 60_000),
        "tx": random.randint(5000, 12000)
    }

# =========================
# Sidebar (控制台)
# =========================
st.sidebar.title("⚙️ 控制台")

api_key = st.sidebar.text_input("API Key", type="password")
stock_code = st.sidebar.text_input("股票代碼", "2330")

refresh_rate = st.sidebar.slider(
    "更新頻率（秒）",
    min_value=1,
    max_value=10,
    value=st.session_state.refresh_rate
)

st.session_state.refresh_rate = refresh_rate

st.sidebar.markdown("---")

colA, colB = st.sidebar.columns(2)

if colA.button("▶ 開始"):
    st.session_state.running = True

if colB.button("⛔ 停止"):
    st.session_state.running = False

st.sidebar.markdown(f"### 狀態：{'🟢 ON' if st.session_state.running else '🔴 OFF'}")
st.sidebar.markdown(f"### ⏱ 更新頻率：{refresh_rate} 秒")

# =========================
# Data
# =========================
data = get_price_data()

is_up = data["change"] >= 0

color = "#ff3b30" if not is_up else "#00c853"
arrow = "▲" if is_up else "▼"

# =========================
# Top Header (交易室風格)
# =========================
st.markdown(f"""
# ⚡ {data['name']} {data['code']}
""")

price_col, info_col = st.columns([1, 3])

with price_col:
    st.markdown(f"""
    <div style="padding:20px;background:#111;border-radius:12px">
        <div style="font-size:42px;font-weight:800;color:{color}">
            {data['price']}
        </div>
        <div style="color:{color};font-size:16px">
            {arrow} {data['change']} ({data['pct']}%)
        </div>
    </div>
    """, unsafe_allow_html=True)

with info_col:
    st.markdown(f"""
    <div style="display:flex;gap:20px;padding:10px">
        <div>成交金額<br><b>{data['amount']:,}</b></div>
        <div>成交量<br><b>{data['volume']:,}</b></div>
        <div>成交筆數<br><b>{data['tx']:,}</b></div>
    </div>
    """, unsafe_allow_html=True)

# =========================
# 五檔報價（券商標準版）
# =========================
st.markdown("## 📊 五檔報價")

bid_col, ask_col = st.columns(2)

with bid_col:
    st.markdown("### 🟢 買方")
    st.markdown("價格　　張數")
    for p, v in data["bids"]:
        st.markdown(f"**{p}**　　🟢 {v}")

with ask_col:
    st.markdown("### 🔴 賣方")
    st.markdown("張數　　價格")
    for p, v in data["asks"]:
        st.markdown(f"🔴 {v}　　**{p}**")

# =========================
# Auto Refresh（無閃爍版）
# =========================
placeholder = st.empty()

if st.session_state.running:
    time.sleep(st.session_state.refresh_rate)
    st.session_state.last_update = time.time()
    st.rerun()

# =========================
# Footer
# =========================
st.markdown("---")
st.caption(f"最後更新時間：{datetime.now().strftime('%H:%M:%S')}")
