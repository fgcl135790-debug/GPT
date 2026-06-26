import streamlit as st
import time

from data.fugle_ws import FugleWS
from core.engine import Engine
from ai.signal import SignalEngine

st.set_page_config(layout="wide")

st.title("🇹🇼 台股 AI 監控系統 v1")

api_key = st.text_input("Fugle API Key", type="password")
symbol = st.text_input("股票代碼", "2330")

if st.button("開始監控"):

    ws = FugleWS(api_key, symbol)
    ws.start()

    engine = Engine()
    ai = SignalEngine()

    chart = st.empty()
    info = st.empty()

    while True:

        if len(ws.prices) < 10:
            time.sleep(1)
            continue

        df = engine.build(ws.prices)

        signal, score = ai.get_signal(df)

        with info.container():
            col1, col2, col3 = st.columns(3)

            col1.metric("即時價格", ws.price)
            col2.metric("AI訊號", signal)
            col3.metric("強度", f"{score}/100")

        with chart.container():
            st.line_chart(df["close"])

        time.sleep(1)
