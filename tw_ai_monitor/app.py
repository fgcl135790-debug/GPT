import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime
import time

# =========================
# UI CONFIG
# =========================
st.set_page_config(page_title="AI 監控 V5", layout="wide")

# =========================
# MOCK 即時資料（之後可換 Fugle）
# =========================
def get_price(symbol="2330"):
    # 模擬即時價格（避免 API 依賴炸裂）
    base = 2340
    noise = np.random.randn() * 2
    return round(base + noise, 2)

def get_vwap():
    return round(2335 + np.random.randn() * 1.5, 2)

def get_volume():
    return int(10000 + np.random.randn() * 2000)

# =========================
# AI SIGNAL LOGIC（簡化版當沖）
# =========================
def ai_signal(price, vwap):
    diff = price - vwap

    if diff > 3:
        return "📈 偏多（回踩可做多）", 75
    elif diff < -3:
        return "📉 偏空（反彈可做空）", 75
    else:
        return "⚖️ 盤整（觀望）", 50

# =========================
# SIDEBAR 控制台
# =========================
st.sidebar.title("⚙️ 控制台")

symbol = st.sidebar.text_input("股票代碼", "2330")
refresh = st.sidebar.slider("更新頻率(秒)", 1, 10, 2)

st.sidebar.write(f"📡 狀態：{'ON' if st.button('停止') else 'RUN'}")
st.sidebar.write(f"⏱ 更新：{refresh}s")

# =========================
# MAIN HEADER（修正你要的股名）
# =========================
st.markdown(f"""
# ⚡ {symbol} AI 即時監控系統
""")

price = get_price(symbol)
vwap = get_vwap()
volume = get_volume()

signal, score = ai_signal(price, vwap)

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("現價", price)

with col2:
    st.metric("VWAP", vwap)

with col3:
    st.metric("成交量", volume)

# =========================
# SIGNAL PANEL
# =========================
st.markdown("## 🧠 AI 當沖判斷")

if "多" in signal:
    st.success(signal)
elif "空" in signal:
    st.error(signal)
else:
    st.warning(signal)

st.progress(score / 100)

# =========================
# ORDERBOOK MOCK（五檔）
# =========================
st.markdown("## 📊 五檔報價")

buy = pd.DataFrame({
    "買價": [2335, 2330, 2325, 2320, 2315],
    "張數": np.random.randint(100, 1200, 5)
})

sell = pd.DataFrame({
    "賣價": [2340, 2345, 2350, 2355, 2360],
    "張數": np.random.randint(100, 1200, 5)
})

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🟢 買方")
    st.dataframe(buy)

with col2:
    st.markdown("### 🔴 賣方")
    st.dataframe(sell)

# =========================
# INFO PANEL
# =========================
st.markdown("## 📦 成交資訊")

c1, c2, c3 = st.columns(3)

c1.metric("成交金額", f"{int(price*10000):,}")
c2.metric("成交張數", f"{volume}")
c3.metric("時間", datetime.now().strftime("%H:%M:%S"))

# =========================
# AUTO REFRESH
# =========================
time.sleep(refresh)
st.rerun()
