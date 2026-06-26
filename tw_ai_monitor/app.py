import streamlit as st
import time

from data.fugle_ws import FugleWS
from core.engine_v2 import EngineV2
from ai.signal_v2 import SignalV2
from ui.dashboard_v3 import run_dashboard

st.set_page_config(layout="wide")

st.title("TW AI Monitor")

api_key = st.text_input("Fugle API Key", type="password")
symbol = st.text_input("股票代碼", "2330")

if st.button("開始監控"):

    ws = FugleWS(api_key, symbol)
    ws.start()

    engine = EngineV2()
    ai = SignalV2()

    placeholder = st.empty()

    while True:

        if len(ws.prices) < 20:
            time.sleep(1)
            continue

        df = engine.build(ws.prices, ws.volumes)

        signal, score = ai.score(df)

        with placeholder.container():
            run_dashboard(df, signal, score, ws)

        time.sleep(1)
