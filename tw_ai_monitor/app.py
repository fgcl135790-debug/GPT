import streamlit as st
import pandas as pd
import numpy as np

from datetime import datetime
from zoneinfo import ZoneInfo

from fugle_provider import FugleProvider
from simulation_engine import SimulationEngine
from market_analyzer import MarketAnalyzer
from ai_predictor import AIPredictor
from charts import ChartBuilder
from exporters import Exporter
from streamlit_autorefresh import st_autorefresh


# =========================
# V4.6 券商級 UI
# =========================

st.set_page_config(
    page_title="V4.6 券商級主力系統",
    page_icon="📊",
    layout="wide"
)

st.markdown("""
<style>
html, body, [class*="css"]  {
    font-size: 13px;
}
.block-container{
    padding: 0.5rem 1rem;
}
</style>
""", unsafe_allow_html=True)


now = datetime.now(ZoneInfo("Asia/Taipei"))

def init_state():
    defaults = {
        "price_history": [],
        "volume_history": [],
        "big_order_log": [],
        "tick": 0,
        "last_trade": None,
        "current_stock": None
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

with st.sidebar:

    st.title("⚙️ V4.6 券商控制中心")

    data_source = st.radio("資料來源", ["真實盤", "情境模擬"])

    stock_code = st.text_input("股票代號", "2330")

    api_key = st.text_input("API Key", type="password")

    sim_mode = st.selectbox(
        "模擬模式",
        ["一般波動", "軋空", "出貨", "吸籌", "崩盤"]
    )

    refresh_sec = st.slider("刷新秒數", 1, 10, 2)

    auto_threshold = st.checkbox("自動大戶偵測", True)

    sim_minutes = st.slider("模擬時間", 2, 60, 10)

st_autorefresh(interval=refresh_sec * 1000, key="refresh")


# =========================
# 換股自動清空（你 bug 的核心修復）
# =========================

if st.session_state.current_stock != stock_code:
    st.session_state.price_history = []
    st.session_state.volume_history = []
    st.session_state.big_order_log = []
    st.session_state.tick = 0
    st.session_state.current_stock = stock_code


try:
    if data_source == "真實盤":
        if not api_key:
            st.warning("請輸入 API KEY")
            st.stop()

        provider = FugleProvider(api_key)
        quote = provider.get_quote(stock_code)

    else:
        engine = SimulationEngine(mode=sim_mode, base_price=100)
        quote = engine.generate(st.session_state.tick, sim_minutes * 60)
        st.session_state.tick += 1

except Exception as e:
    st.error(f"資料錯誤：{e}")
    st.stop()

name = quote.get("name", "UNKNOWN")
price = float(quote.get("price", 0))
vwap = float(quote.get("vwap", price))
volume = quote.get("last_size", 0)

bids = quote.get("bids") or []
asks = quote.get("asks") or []

trade = quote.get("trade") or {}
trade_serial = trade.get("serial", 0)

is_close = quote.get("is_close", False)


market_open = 9 <= now.hour <= 13

if market_open and not is_close:

    if (len(st.session_state.price_history) == 0
        or st.session_state.last_trade != trade_serial):

        st.session_state.last_trade = trade_serial

        st.session_state.price_history.append(price)
        st.session_state.volume_history.append(volume)


# 保護：避免 NaN 導致圖空白
prices = [p for p in st.session_state.price_history if p is not None]
volumes = [v for v in st.session_state.volume_history if v is not None]

prices = prices[-300:]
volumes = volumes[-300:]

ema5 = MarketAnalyzer.calculate_ema(prices, 5)
ema20 = MarketAnalyzer.calculate_ema(prices, 20)
ema60 = MarketAnalyzer.calculate_ema(prices, 60)

rsi = MarketAnalyzer.calculate_rsi(prices)
macd, macd_signal, macd_hist = MarketAnalyzer.calculate_macd(prices)

momentum = MarketAnalyzer.momentum(prices)
volatility = MarketAnalyzer.volatility(prices)

total_bid = sum(x.get("size", 0) for x in bids)
total_ask = sum(x.get("size", 0) for x in asks)

bid_ratio = total_bid / max(total_ask, 1)

ai_score = 50

if price > vwap:
    ai_score += 10
else:
    ai_score -= 10

if ema5 > ema20:
    ai_score += 10
else:
    ai_score -= 10

if rsi < 30:
    ai_score += 10
elif rsi > 70:
    ai_score -= 10

if macd > macd_signal:
    ai_score += 10
else:
    ai_score -= 10

if bid_ratio > 1.5:
    ai_score += 15
else:
    ai_score -= 10

ai_score = max(0, min(100, int(ai_score)))


# =========================
# 反轉區（修正你說的「消失問題」）
# =========================

if ema5 > ema20 and rsi < 40:
    reversal = "BUY"
elif ema5 < ema20 and rsi > 60:
    reversal = "SELL"
else:
    reversal = "WATCH"

st.title(f"{name} ({stock_code})")

st.subheader("📈 即時走勢")

# 🔥 修復：空資料不畫圖
if len(prices) > 1:
    fig = ChartBuilder.build_price_chart(prices, volumes)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("等待資料中...")

st.subheader("🔄 反轉區")

if reversal == "BUY":
    st.success("📈 可能反彈（短多訊號）")
elif reversal == "SELL":
    st.error("📉 可能轉弱（短空訊號）")
else:
    st.info("⚖️ 盤整觀望")
