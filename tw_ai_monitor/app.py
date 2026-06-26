import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import datetime as dt

# =========================
# UI CONFIG
# =========================
st.set_page_config(layout="wide", page_title="AI 實戰監控系統")

# =========================
# STYLE (券商級暗色)
# =========================
st.markdown("""
<style>
body {
    background-color: #0e1117;
    color: white;
}

.block {
    background: #151a22;
    padding: 16px;
    border-radius: 12px;
    margin-bottom: 12px;
}

.title {
    font-size: 26px;
    font-weight: 800;
}

.price-up { color: #00c853; font-size: 42px; font-weight: 800; }
.price-down { color: #ff5252; font-size: 42px; font-weight: 800; }

.tag-long { color: #00e676; font-weight: 700; }
.tag-short { color: #ff1744; font-weight: 700; }
.tag-wait { color: #ffd600; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# =========================
# SIDEBAR CONTROL PANEL
# =========================
st.sidebar.title("⚙️ 控制台")

symbol = st.sidebar.text_input("股票代碼", "2330.TW")
refresh = st.sidebar.slider("更新秒數", 1, 10, 2)

start = st.sidebar.button("開始監控")
stop = st.sidebar.button("停止")

# =========================
# DATA
# =========================
def load_data(symbol):
    df = yf.download(symbol, period="1d", interval="1m")
    df = df.dropna()
    return df

def vwap(df):
    return (df["Close"] * df["Volume"]).cumsum() / df["Volume"].cumsum()

def ema(df, n):
    return df["Close"].ewm(span=n).mean()

# =========================
# SIGNAL ENGINE（核心）
# =========================
def signal_logic(df):
    df["VWAP"] = vwap(df)
    df["EMA5"] = ema(df, 5)
    df["EMA20"] = ema(df, 20)

    last = df.iloc[-1]

    score = 0

    # VWAP
    if last["Close"] > last["VWAP"]:
        score += 25
    else:
        score -= 25

    # EMA trend
    if last["EMA5"] > last["EMA20"]:
        score += 25
    else:
        score -= 25

    # momentum
    if df["Close"].iloc[-1] > df["Close"].iloc[-3]:
        score += 10
    else:
        score -= 10

    # decision
    if score >= 30:
        signal = "📈 做多"
    elif score <= -30:
        signal = "📉 做空"
    else:
        signal = "⏸ 觀望"

    return df, score, signal

# =========================
# MAIN PANEL
# =========================
st.markdown("## ⚡ AI 實戰交易監控系統（專業版）")

df = load_data(symbol)
df, score, signal = signal_logic(df)

last_price = df["Close"].iloc[-1]

# =========================
# TOP INFO CARD
# =========================
col1, col2, col3 = st.columns([2,2,2])

with col1:
    st.markdown("### 股票")
    st.markdown(f"## {symbol}")

with col2:
    color = "price-up" if score > 0 else "price-down"
    st.markdown(f'<div class="{color}">{round(last_price,2)}</div>', unsafe_allow_html=True)

with col3:
    st.markdown("### 訊號")
    if "做多" in signal:
        st.markdown(f'<div class="tag-long">{signal}</div>', unsafe_allow_html=True)
    elif "做空" in signal:
        st.markdown(f'<div class="tag-short">{signal}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="tag-wait">{signal}</div>', unsafe_allow_html=True)

st.markdown("---")

# =========================
# CHART AREA
# =========================
st.markdown("### 📊 價格 / VWAP / 均線")

chart_df = df.copy()
chart_df = chart_df[["Close"]]
st.line_chart(chart_df)

# =========================
# AI SCORE PANEL
# =========================
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### VWAP")
    st.write(round(df["VWAP"].iloc[-1], 2))

with col2:
    st.markdown("### EMA5")
    st.write(round(df["EMA5"].iloc[-1], 2))

with col3:
    st.markdown("### EMA20")
    st.write(round(df["EMA20"].iloc[-1], 2))

st.markdown("---")

# =========================
# AI DECISION PANEL（重點）
# =========================
st.markdown("## 🧠 AI 當沖判斷核心")

if score > 30:
    st.success(f"偏多格局（Score: {score}）→ 以回踩做多為主")
elif score < -30:
    st.error(f"偏空格局（Score: {score}）→ 以反彈放空為主")
else:
    st.warning(f"盤整區（Score: {score}）→ 不建議追價")

# =========================
# FOOTER
# =========================
st.caption("AI Monitor v2 | VWAP + EMA + Momentum Engine")
