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

if st.button("開始監控"):

    ws = FugleWS(api_key, symbol)
    ws.start()

    engine = EngineV2()
    ai = SignalV2()

    placeholder = st.empty()

    while True:

        # ======================
        # 1️⃣ WS 有資料就用 WS
        # ======================
        if len(ws.prices) > 20:
            df = engine.build(ws.prices, ws.volumes)

        else:
            # ======================
            # 2️⃣ fallback REST
            # ======================
            price = get_price(symbol, api_key)

            if price is None:
                st.write("等待資料中...")
                time.sleep(1)
                continue

            df = engine.build([price], [1])

        # ======================
        # 3️⃣ AI
        # ======================
        signal, score = ai.score(df)

        # ======================
        # 4️⃣ UI
        # ======================
        with placeholder.container():
            run_dashboard(df, signal, score, ws)

        time.sleep(1)
