import streamlit as st
import pandas as pd
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
# V4.6 券商級設定
# =========================

st.set_page_config(
    page_title="V4.6 券商級主力系統",
    page_icon="🏦",
    layout="wide"
)

st.markdown("""
<style>
.block-container{
    padding:0.4rem 0.8rem;
    font-size: 13px;
}

/* 台股風格：紅漲綠跌 */
.positive { color:#ff4d4f; }
.negative { color:#00c853; }

/* 壓縮UI */
h1 { font-size: 22px !important; }
h2 { font-size: 18px !important; }
h3 { font-size: 15px !important; }
</style>
""", unsafe_allow_html=True)

now = datetime.now(ZoneInfo("Asia/Taipei"))

def reset_state():
    st.session_state.price_history = []
    st.session_state.volume_history = []
    st.session_state.big_order_log = []
    st.session_state.tick = 0
    st.session_state.last_symbol = None
    st.session_state.last_trade_serial = None


for k in [
    "price_history",
    "volume_history",
    "big_order_log",
    "tick",
    "last_symbol",
    "last_trade_serial"
]:
    if k not in st.session_state:
        st.session_state[k] = [] if "history" in k or "log" in k else 0

with st.sidebar:
    st.title("⚙️ V4.6 券商控制中心")

    data_source = st.radio("資料來源", ["真實盤", "情境模擬"])

    stock_code = st.text_input("股票代號", "2330")

    api_key = st.text_input("API Key", type="password")

    sim_mode = st.selectbox("模擬", ["一般", "軋空", "出貨", "吸籌"])

    refresh_sec = st.slider("更新秒數", 1, 10, 2)

    if st.button("🔄 換股 / 重置"):
        reset_state()
        st.rerun()

st_autorefresh(interval=refresh_sec * 1000, key="v46")

try:
    if data_source == "真實盤":
        if not api_key:
            st.warning("請輸入API")
            st.stop()

        provider = FugleProvider(api_key)
        quote = provider.get_quote(stock_code)

    else:
        engine = SimulationEngine(mode=sim_mode, base_price=100)

        quote = engine.generate(
            st.session_state.tick,
            300
        )

        st.session_state.tick += 1

except Exception as e:
    st.error(f"資料錯誤: {e}")
    st.stop()

name = quote["name"]
price = quote["price"]
vwap = quote["vwap"]
volume = quote.get("last_size", 0)

bids = quote.get("bids", [])
asks = quote.get("asks", [])

trade = quote.get("trade", {})
trade_serial = trade.get("serial", 0)

# 👉 換股票自動清空（核心修復）
if st.session_state.get("last_symbol") != stock_code:
    reset_state()
    st.session_state.last_symbol = stock_code
    st.rerun()

st.title(f"🏦 {name} {stock_code}")

st.subheader("📈 券商級走勢圖")

fig = ChartBuilder.build_price_chart(
    st.session_state.price_history,
    st.session_state.volume_history
)

st.plotly_chart(
    fig,
    use_container_width=True,
    height=520  # ✔ 防止被切
)

ema5 = MarketAnalyzer.calculate_ema(st.session_state.price_history, 5)
ema20 = MarketAnalyzer.calculate_ema(st.session_state.price_history, 20)
rsi = MarketAnalyzer.calculate_rsi(st.session_state.price_history)

total_bid = sum(x["size"] for x in bids)
total_ask = sum(x["size"] for x in asks)

bid_ratio = total_bid / max(total_ask, 1)

# =========================
# 進出場訊號（新增）
# =========================

if ema5 > ema20 and rsi < 70:
    signal = "BUY"
elif ema5 < ema20 and rsi > 30:
    signal = "SELL"
else:
    signal = "HOLD"

# =========================
# 主力雷達（新增）
# =========================

flow = total_bid - total_ask

if flow > 0:
    radar = "🔴 主力進場"
elif flow < 0:
    radar = "🟢 主力出場"
else:
    radar = "🟡 觀望"

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("現價", price)

with col2:
    st.metric("VWAP", vwap)

with col3:
    st.metric("RSI", rsi)

st.subheader("🔄 反轉雷達")

if signal == "BUY":
    st.success("📈 多方進場訊號")
elif signal == "SELL":
    st.error("📉 空方轉弱訊號")
else:
    st.info("⚖️ 盤整中")

st.subheader("📡 主力雷達")

st.write(radar)

st.progress(
    min(abs(flow) / (total_bid + total_ask + 1), 1)
)

