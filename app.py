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
# Page Config
# =========================

st.set_page_config(

    page_title="REST PRO v3",

    page_icon="📈",

    layout="wide",

)

st.markdown(
    """
<style>

.block-container{

    padding-top:0.5rem;
    padding-bottom:0.5rem;
    padding-left:1rem;
    padding-right:1rem;

}

</style>
""",
    unsafe_allow_html=True,
)

# =========================
# 台灣時間
# =========================

now = datetime.now(
    ZoneInfo("Asia/Taipei")
)

# =========================
# Session State
# =========================

if "price_history" not in st.session_state:

    st.session_state.price_history = []

if "volume_history" not in st.session_state:

    st.session_state.volume_history = []

if "big_order_log" not in st.session_state:

    st.session_state.big_order_log = []

if "last_history_serial" not in st.session_state:

    st.session_state.last_history_serial = None

if "last_big_order_serial" not in st.session_state:

    st.session_state.last_big_order_serial = None

if "tick" not in st.session_state:

    st.session_state.tick = 0

avg_volume = 1
suggest_threshold = 100

# =========================
# Sidebar
# =========================

with st.sidebar:

    st.header("⚙️ 系統設定")

    data_source = st.radio(

        "資料來源",

        [

            "真實盤",

            "情境模擬",

        ],

    )

    stock_code = st.text_input(

        "股票代號",

        "2330",

    )

    api_key = st.text_input(

        "Fugle API Key",

        type="password",

    )

    sim_mode = st.selectbox(

        "模擬情境",

        [

            "一般波動",

            "漲停鎖死",

            "跌停鎖死",

            "跳空急跌",

            "軋空行情",

            "誘多出貨",

            "誘空嘎空",

            "拉高出貨",

            "主力吸籌",

        ],

    )

    # ---------------------
    # 大戶門檻
    # ---------------------

    auto_threshold = st.checkbox(

        "自動大戶門檻",

        value=True,

    )

    if len(st.session_state.volume_history) > 0:

        avg_volume = (

            sum(
                st.session_state.volume_history[-100:]
            )

            /

            min(
                len(st.session_state.volume_history),
                100,
            )

        )

        suggest_threshold = int(

            avg_volume * 3

        )

        st.info(

            f"最近100筆平均量：{avg_volume:.0f} 張\n\n"

            f"建議大戶門檻：{suggest_threshold} 張"

        )

    if auto_threshold:

        big_order_threshold = suggest_threshold

        st.success(

            f"目前使用自動門檻：{big_order_threshold} 張"

        )

    else:

        big_order_threshold = st.number_input(

            "大戶門檻",

            min_value=10,

            max_value=10000,

            value=100,

            step=10,

        )

    sim_minutes = st.slider(

        "模擬分鐘",

        2,

        60,

        10,

    )

    if st.button("重置模擬"):

        st.session_state.price_history = []

        st.session_state.volume_history = []

        st.session_state.big_order_log = []

        st.session_state.last_history_serial = None

        st.session_state.last_big_order_serial = None

        st.session_state.tick = 0

        st.rerun()

# =========================
# Data Provider
# =========================

try:

    if data_source == "真實盤":

        if api_key == "":

            st.warning(
                "請輸入 Fugle API Key"
            )

            st.stop()

        provider = FugleProvider(
            api_key
        )

        quote = provider.get_quote(
            stock_code
        )

    else:

        engine = SimulationEngine(

            mode=sim_mode,

            base_price=100,

        )

        quote = engine.generate(

            st.session_state.tick,

            sim_minutes * 60,

        )

        st.session_state.tick += 1

except Exception as e:

    st.error(

        f"資料取得失敗：{e}"

    )

    st.stop()

# =========================
# Quote
# =========================

name = quote["name"]

price = quote["price"]

vwap = quote["vwap"]

volume = quote["last_size"]

bids = quote["bids"]

asks = quote["asks"]

trade = quote["trade"]

trade_serial = trade.get(

    "serial",

    0,

)

is_close = quote.get(

    "is_close",

    False,

)

# =========================
# 市場是否開盤
# =========================

market_open = (

    (
        now.hour > 9
        or
        (
            now.hour == 9
            and
            now.minute >= 0
        )
    )

    and

    (
        now.hour < 13
        or
        (
            now.hour == 13
            and
            now.minute <= 30
        )
    )

)

# =========================
# 自動更新
# =========================

st_autorefresh(

    interval=2000,

    key="refresh",

)

if is_close:

    st.sidebar.warning(

        "🔴 已收盤"

    )

else:

    st.sidebar.success(

        "🟢 即時更新中"

    )

# =========================
# History
# =========================

if market_open and not is_close:

    if (

        len(st.session_state.price_history) == 0

        or

        trade_serial
        !=
        st.session_state.last_history_serial

    ):

        st.session_state.last_history_serial = trade_serial

        st.session_state.price_history.append(
            price
        )

        st.session_state.volume_history.append(
            volume
        )

st.session_state.price_history = (
    st.session_state.price_history[-500:]
)

st.session_state.volume_history = (
    st.session_state.volume_history[-500:]
)

prices = (
    st.session_state.price_history
)

volumes = (
    st.session_state.volume_history
)

# =========================
# Technical Indicators
# =========================

ema5 = MarketAnalyzer.calculate_ema(
    prices,
    5,
)

ema20 = MarketAnalyzer.calculate_ema(
    prices,
    20,
)

ema60 = MarketAnalyzer.calculate_ema(
    prices,
    60,
)

sma20 = MarketAnalyzer.calculate_sma(
    prices,
    20,
)

trend = MarketAnalyzer.trend(

    price,

    vwap,

    ema5,

    ema20,

)

momentum = MarketAnalyzer.momentum(
    prices
)

volatility = MarketAnalyzer.volatility(
    prices
)

rsi = MarketAnalyzer.calculate_rsi(
    prices
)

macd, macd_signal, macd_hist = (

    MarketAnalyzer.calculate_macd(
        prices
    )

)

volume_trend = (

    MarketAnalyzer.volume_trend(
        volumes
    )

)

# =========================
# 買賣盤統計
# =========================

total_bid = sum(

    x["size"]

    for x in bids

)

total_ask = sum(

    x["size"]

    for x in asks

)

buy_strength = round(

    total_bid

    /

    max(

        total_bid + total_ask,

        1,

    )

    * 100

)

sell_strength = (

    100

    - buy_strength

)

# =========================
# AI 分析
# =========================

action, confidence, reasons = (
    AIPredictor.predict_trade(
        prices=prices,
        volumes=volumes,
        price=price,
        vwap=vwap,
        ema5=ema5,
        ema20=ema20,
        ema60=ema60,
        rsi=rsi,
        macd=macd,
        macd_signal=macd_signal,
        total_bid=total_bid,
        total_ask=total_ask,
    )
)

(
    reversal_signal,
    reversal_text,
    reversal_probability,
    reversal_stars,
    reversal_reasons,
) = (
    AIPredictor.predict_reversal(
        prices=prices,
        price=price,
        ema5=ema5,
        ema20=ema20,
        ema60=ema60,
        rsi=rsi,
        macd=macd,
        macd_signal=macd_signal,
        total_bid=total_bid,
        total_ask=total_ask,
    )
)

# =========================
# Header
# =========================

if is_close:

    st.warning(
        "🔴 已收盤"
    )

else:

    st.success(
        "🟢 即時更新中"
    )

st.title(
    f"⚡ {name} ({stock_code})"
)

st.caption(
    f"更新時間：{now.strftime('%Y-%m-%d %H:%M:%S')}"
)

# =========================
# Price Chart
# =========================

st.subheader(
    "📈 即時走勢"
)

fig = ChartBuilder.build_price_chart(

    prices,

    volumes,

)

st.plotly_chart(

    fig,

    use_container_width=True,

)

# =========================
# 指標列
# =========================

st.markdown("---")

c1, c2, c3, c4, c5, c6 = st.columns(6)

c1.metric(
    "現價",
    round(price, 2),
)

c2.metric(
    "VWAP",
    round(vwap, 2),
)

c3.metric(
    "EMA5",
    round(float(ema5), 2),
)

c4.metric(
    "EMA20",
    round(float(ema20), 2),
)

c5.metric(
    "RSI",
    rsi,
)

c6.metric(
    "MACD",
    macd,
)

st.markdown("---")

# =========================
# AI 分析區
# =========================

left, center, right = st.columns(3)

# =========================
# AI交易判斷
# =========================

with left:

    st.subheader("🤖 AI交易判斷")

    if action == "STRONG BUY":

        st.success(f"🟢 強力買進　{confidence}%")

    elif action == "BUY":

        st.success(f"📈 買進　{confidence}%")

    elif action == "SELL":

        st.error(f"📉 賣出　{confidence}%")

    elif action == "STRONG SELL":

        st.error(f"🔴 強力賣出　{confidence}%")

    else:

        st.warning(f"🟡 觀望　{confidence}%")

    st.progress(confidence / 100)

    st.markdown("#### AI分析")

    for r in reasons:

        st.write("•", r)


# =========================
# AI反轉預測
# =========================

with center:

    st.subheader("🔄 AI反轉預測")

    if reversal_signal == "BUY":

        st.success(reversal_text)

    elif reversal_signal == "WATCH":

        st.warning(reversal_text)

    elif reversal_signal == "SELL":

        st.error(reversal_text)

    else:

        st.info(reversal_text)

    st.metric(
        "AI信心",
        f"{reversal_probability}%"
    )

    st.progress(
        reversal_probability / 100
    )

    st.write(reversal_stars)

    st.markdown("#### AI依據")

    for r in reversal_reasons:

        st.write("•", r)
# =========================
# 技術指標
# =========================

with right:

    st.subheader("📊 技術分析")

    st.metric(
        "Momentum",
        round(momentum, 2)
    )

    if rsi >= 70:
        rsi_state = "🔥 超買"
    elif rsi <= 30:
        rsi_state = "🧊 超賣"
    else:
        rsi_state = "✅ 正常"

    st.metric(
        "RSI",
        f"{rsi} ({rsi_state})"
    )

    if macd > macd_signal:
        macd_state = "🟢 多頭"
    else:
        macd_state = "🔴 空頭"

    st.metric(
        "MACD",
        macd_state
    )

    st.metric(
        "波動率",
        f"{volatility}%"
    )

    st.metric(
        "成交量",
        volume_trend
    )

    st.metric(
        "SMA20",
        round(float(sma20), 2)
    )

    st.metric(
        "MACD Hist",
        round(macd_hist, 3)
    )

st.markdown("---")

# =========================
# AI 綜合評分
# =========================

ai_score = 50

# AI交易分數
if action == "STRONG BUY":
    ai_score += 25
elif action == "BUY":
    ai_score += 15
elif action == "SELL":
    ai_score -= 15
elif action == "STRONG SELL":
    ai_score -= 25

# 反轉預測
if reversal_signal == "BUY":
    ai_score += 15
elif reversal_signal == "SELL":
    ai_score -= 15

# RSI
if rsi < 30:
    ai_score += 10
elif rsi > 70:
    ai_score -= 10

# MACD
if macd > macd_signal:
    ai_score += 10
else:
    ai_score -= 10

# Momentum
if momentum > 0:
    ai_score += 5
else:
    ai_score -= 5

# 買賣盤
if total_bid > total_ask:
    ai_score += 10
else:
    ai_score -= 10

ai_score = max(0, min(ai_score, 100))

st.subheader("🧠 AI 綜合評分")

c1, c2 = st.columns([3, 2])

with c1:

    st.progress(ai_score / 100)

with c2:

    st.metric(
        "AI Score",
        f"{ai_score}/100"
    )

if ai_score >= 85:
    st.success("🚀 極度看多")

elif ai_score >= 70:
    st.success("📈 偏多")

elif ai_score >= 55:
    st.info("🙂 小幅偏多")

elif ai_score >= 45:
    st.warning("😐 中性整理")

elif ai_score >= 30:
    st.warning("📉 偏空")

else:
    st.error("💥 極度看空")

# =========================
# 主力分析
# =========================

st.subheader(
    "🏦 主力分析"
)

institution_score = int(

    total_bid

    /

    max(

        total_bid + total_ask,

        1,

    )

    * 100

)

c1, c2, c3, c4 = st.columns(4)

with c1:

    st.metric(

        "主力分數",

        f"{institution_score}/100",

    )

with c2:

    st.metric(

        "委買",

        total_bid,

    )

with c3:

    st.metric(

        "委賣",

        total_ask,

    )

with c4:

    st.metric(

        "買盤比例",

        f"{buy_strength}%",

    )

st.progress(
    buy_strength / 100
)

# =========================
# 主力狀態
# =========================

bid_ratio = (

    total_bid

    /

    max(total_ask, 1)

)

if bid_ratio >= 2:

    st.success(
        "🟢 主力積極吸籌"
    )

elif bid_ratio >= 1.3:

    st.info(
        "📈 主力偏多"
    )

elif bid_ratio <= 0.5:

    st.error(
        "🔴 主力大量出貨"
    )

elif bid_ratio <= 0.8:

    st.warning(
        "📉 主力偏空"
    )

else:

    st.info(
        "⚪ 主力中性"
    )

# =========================
# 漲停機率
# =========================

limit_score = 0

if price > vwap:

    limit_score += 25

if ema5 > ema20:

    limit_score += 25

if bid_ratio > 1.5:

    limit_score += 25

if momentum > 2:

    limit_score += 25

limit_score = min(
    limit_score,
    100,
)

st.metric(

    "🚀 漲停機率",

    f"{limit_score}%",

)

st.progress(
    limit_score / 100
)

st.markdown("---")

# =========================
# 大戶成交偵測
# =========================

if (

    market_open

    and

    not is_close

    and

    volume >= big_order_threshold

    and

    trade_serial

    !=

    st.session_state.last_big_order_serial

):

    st.session_state.last_big_order_serial = trade_serial

    impact_ratio = round(

        volume

        /

        max(avg_volume, 1),

        2,

    )

    # =====================
    # 大戶等級
    # =====================

    if volume >= 5000:

        level = "🐋 超級主力"

    elif volume >= 2000:

        level = "🔥 主力大單"

    elif volume >= 800:

        level = "🏦 法人等級"

    else:

        level = "💰 大戶"

    # =====================
    # 買賣方向
    # =====================

    if total_bid > total_ask:

        direction = "🟢 主力買進"

    elif total_ask > total_bid:

        direction = "🔴 主力賣出"

    else:

        direction = "⚪ 中性"

    # =====================
    # AI判斷
    # =====================

    ai_tag = action

    # =====================
    # 寫入紀錄
    # =====================

    st.session_state.big_order_log.insert(

        0,

        {

            "時間": now.strftime("%H:%M:%S"),

            "價格": round(price, 2),

            "張數": volume,

            "等級": level,

            "方向": direction,

            "影響力": f"{impact_ratio} 倍",

            "AI": ai_tag,

            "來源": data_source,

        },

    )

# 只保留最新200筆

st.session_state.big_order_log = (

    st.session_state.big_order_log[:200]

)

# =========================
# 主力統計
# =========================

buy_count = 0

sell_count = 0

for row in st.session_state.big_order_log:

    if "買進" in row["方向"]:

        buy_count += 1

    elif "賣出" in row["方向"]:

        sell_count += 1

net_flow = buy_count - sell_count

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "主力買進",
    buy_count,
)

c2.metric(
    "主力賣出",
    sell_count,
)

c3.metric(
    "淨流向",
    net_flow,
)

c4.metric(
    "大戶門檻",
    f"{big_order_threshold} 張",
)

st.markdown("---")

# =========================
# 大戶成交紀錄
# =========================

st.subheader(
    "📜 大戶成交紀錄"
)

if len(st.session_state.big_order_log) > 0:

    log_df = pd.DataFrame(
        st.session_state.big_order_log
    )

    st.dataframe(

        log_df,

        use_container_width=True,

        hide_index=True,

    )

else:

    st.info(
        "尚未偵測到大戶成交"
    )

# =========================
# Best 5
# =========================

st.markdown("---")

st.subheader(
    "📋 最佳五檔"
)

while len(bids) < 5:

    bids.append({

        "price": 0,

        "size": 0,

    })

while len(asks) < 5:

    asks.append({

        "price": 0,

        "size": 0,

    })

best5_df = pd.DataFrame({

    "買張": [

        x["size"]

        for x in bids[:5]

    ],

    "買價": [

        x["price"]

        for x in bids[:5]

    ],

    "賣價": [

        x["price"]

        for x in asks[:5]

    ],

    "賣張": [

        x["size"]

        for x in asks[:5]

    ],

})

st.dataframe(

    best5_df,

    use_container_width=True,

    hide_index=True,

)

# =========================
# 匯出
# =========================

st.markdown("---")

st.subheader(
    "📥 匯出資料"
)

csv_data = Exporter.export_big_order_log(

    st.session_state.big_order_log

)

st.download_button(

    "📥 下載大戶成交紀錄",

    csv_data,

    file_name="big_order_log.csv",

    mime="text/csv",

)

# =========================
# Footer
# =========================

st.markdown("---")

st.caption(
    "REST PRO v3 | AI Order Flow Analyzer"
)

st.caption(

    f"更新時間：{now.strftime('%Y-%m-%d %H:%M:%S')}"

)

