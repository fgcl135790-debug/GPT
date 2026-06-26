import streamlit as st
import time

from data.fugle_ws import FugleWS
from core.engine_v2 import EngineV2
from ai.signal_v2 import SignalV2

st.set_page_config(layout="wide")

st.title("🇹🇼 台股 AI 監控 v2（專業版）")

api_key = st.text_input("Fugle API Key", type="password")
symbol = st.text_input("股票代碼", "2330")

if st.button("開始監控"):

    ws = FugleWS(api_key, symbol)
    ws.start()

    engine = EngineV2()
    ai = SignalV2()

    chart = st.empty()
    panel = st.empty()

    while True:

        if len(ws.prices) < 20:
            time.sleep(1)
            continue

        df = engine.build(ws.prices, ws.volumes)

        signal, score = ai.score(df)

        with panel.container():

            col1, col2, col3 = st.columns(3)

            col1.metric("即時價格", ws.price)
            col2.metric("AI訊號", signal)
            col3.metric("強度", f"{score}/100")

        with chart.container():
            st.line_chart(df[["close", "vwap"]])

        time.sleep(1)
