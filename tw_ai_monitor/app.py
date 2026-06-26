import streamlit as st
import time

from data.fugle_ws import FugleWS
from data.fugle_rest import get_price
from core.engine_v2 import EngineV2
from ai.signal_v2 import SignalV2
from ui.dashboard_v3 import run_dashboard

st.set_page_config(layout="wide")

st.title("TW AI Monitor v3 Hybrid (WS + REST)")

api_key = st.text_input("Fugle API Key", type="password")
symbol = st.text_input("股票代碼", "2330")

# =========================
# session state 初始化
# =========================
if "ws" not in st.session_state:
    st.session_state.ws = None
    st.session_state.engine = EngineV2()
    st.session_state.ai = SignalV2()
    st.session_state.running = False

# =========================
# 開始按鈕
# =========================
if st.button("開始監控"):
    st.session_state.ws = FugleWS(api_key, symbol)
    st.session_state.ws.start()
    st.session_state.running = True

# =========================
# auto refresh（關鍵）
# =========================
if st.session_state.running:
    st.autorefresh(interval=1000, key="refresh")

    ws = st.session_state.ws
    engine = st.session_state.engine
    ai = st.session_state.ai

    status = st.empty()
    chart = st.empty()

    df = None

    # =========================
    # 1️⃣ WS 有資料
    # =========================
    if ws and len(ws.prices) > 20:
        df = engine.build(ws.prices, ws.volumes)
        status.write("📡 WS 模式")

    else:
        # =========================
        # 2️⃣ REST fallback
        # =========================
        price = get_price(symbol, api_key)

        if price is None:
            status.write("⏳ 等待資料中...")
            st.stop()
        else:
            df = engine.build([price], [1])
            status.write("🌐 REST 模式")

    # =========================
    # 3️⃣ AI
    # =========================
    signal, score = ai.score(df)

    # =========================
    # 4️⃣ UI
    # =========================
    with chart:
        run_dashboard(df, signal, score, ws)
