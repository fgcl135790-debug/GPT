import streamlit as st
import yfinance as yf
import numpy as np
import pandas as pd

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="AI Trading V5",
    layout="wide"
)

# =========================
# STYLE
# =========================
st.markdown("""
<style>
body { background-color: #0e1117; color: white; }

.card {
    background: #151a22;
    padding: 16px;
    border-radius: 14px;
    margin-bottom: 12px;
}

.big {
    font-size: 40px;
    font-weight: 800;
}

.up { color: #00e676; }
.down { color: #ff5252; }
.wait { color: #ffd600; }

.title {
    font-size: 24px;
    font-weight: 800;
}
</style>
""", unsafe_allow_html=True)

# =========================
# SIDEBAR
# =========================
st.sidebar.title("⚙️ AI Trading V5")

symbol = st.sidebar.text_input("股票代碼", "2330.TW")
risk_mode = st.sidebar.selectbox("策略模式", ["一般", "積極當沖", "保守"])

run = st.sidebar.button("開始分析")

# =========================
# DATA
# =========================
@st.cache_data(ttl=5)
def get_data(symbol):
    df = yf.download(symbol, period="1d", interval="1m")
    df = df.dropna()
    return df

def VWAP(df):
    return (df["Close"] * df["Volume"]).cumsum() / df["Volume"].cumsum()

def EMA(df, n):
    return df["Close"].ewm(span=n).mean()

# =========================
# FALSE BREAKOUT DETECTOR
# =========================
def fake_breakout(df):
    high = df["Close"].rolling(10).max()
    low = df["Close"].rolling(10).min()

    last = df["Close"].iloc[-1]

    # 假突破上緣後跌回
    if last < high.iloc[-2] and df["Close"].iloc[-2] > high.iloc[-3]:
        return -1

    # 假跌破後拉回
    if last > low.iloc[-2] and df["Close"].iloc[-2] < low.iloc[-3]:
        return 1

    return 0

# =========================
# AI ENGINE V5
# =========================
def ai_engine(df):

    df["VWAP"] = VWAP(df)
    df["EMA5"] = EMA(df, 5)
    df["EMA20"] = EMA(df, 20)
    df["EMA60"] = EMA(df, 60)

    last = df.iloc[-1]

    score = 0

    # 1. VWAP（核心）
    if last["Close"] > last["VWAP"]:
        score += 30
    else:
        score -= 30

    # 2. 趨勢
    if last["EMA5"] > last["EMA20"] > last["EMA60"]:
        score += 30
    elif last["EMA5"] < last["EMA20"] < last["EMA60"]:
        score -= 30

    # 3. momentum
    if df["Close"].iloc[-1] > df["Close"].iloc[-5]:
        score += 10
    else:
        score -= 10

    # 4. 假突破
    fb = fake_breakout(df)
    score += fb * 25

    # =========================
    # SIGNAL LOGIC
    # =========================
    if score >= 40:
        signal = "📈 做多"
        action = "回踩 VWAP 做多"
    elif score <= -40:
        signal = "📉 做空"
        action = "反彈放空"
    else:
        signal = "⏸ 觀望"
        action = "等待假突破或趨勢確認"

    # =========================
    # RISK ZONE
    # =========================
    price = last["Close"]
    vwap = last["VWAP"]

    stop_loss = vwap * 0.995
    take_profit = vwap * 1.01

    return df, score, signal, action, price, vwap, stop_loss, take_profit

# =========================
# RUN
# =========================
if run:

    df = get_data(symbol)
    df, score, signal, action, price, vwap, sl, tp = ai_engine(df)

    # =========================
    # HEADER
    # =========================
    st.markdown("## ⚡ AI Trading V5（實戰監控版）")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 價格")
        st.markdown(f"<div class='big'>{round(price,2)}</div>", unsafe_allow_html=True)

    with col2:
        st.markdown("### VWAP")
        st.markdown(f"<div class='big'>{round(vwap,2)}</div>", unsafe_allow_html=True)

    with col3:
        if score > 0:
            st.markdown(f"<div class='big up'>{signal}</div>", unsafe_allow_html=True)
        elif score < 0:
            st.markdown(f"<div class='big down'>{signal}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='big wait'>{signal}</div>", unsafe_allow_html=True)

    # =========================
    # CHART
    # =========================
    st.markdown("## 📊 即時價格")
    st.line_chart(df["Close"])

    # =========================
    # AI DECISION
    # =========================
    st.markdown("## 🧠 AI 判斷引擎")

    st.write("📌 判斷理由：", action)
    st.write("📊 Score：", score)

    # =========================
    # RISK CONTROL
    # =========================
    st.markdown("## 🛑 風控區")

    col1, col2 = st.columns(2)

    with col1:
        st.error(f"停損區：{round(sl,2)}")

    with col2:
        st.success(f"停利區：{round(tp,2)}")

    # =========================
    # STRATEGY EXPLANATION
    # =========================
    st.markdown("## 📘 策略邏輯")

    st.info("""
    V5策略核心：

    1. VWAP（主多空分界）
    2. EMA 5/20/60 趨勢排列
    3. Momentum（短線動能）
    4. 假突破偵測（掃停損行情）
    5. VWAP回歸交易模型
    """)
