import streamlit as st
import time

from data.fugle_ws import FugleWS
from data.fugle_rest import FugleREST
from ai.signal_v2 import score
from ui.dashboard_v3 import run_dashboard

st.set_page_config(layout="wide")

st.title("TW AI Monitor v3 Hybrid (WS + REST)")

api_key = st.text_input("Fugle API Key", type="password")
symbol = st.text_input("股票代碼", "2330")

start = st.button("開始監控")

if start:

    ws = FugleWS(api_key, symbol)
    ws.start()

    rest = FugleREST(api_key)

    placeholder = st.empty()

    while True:

        if len(ws.prices) < 20:
            time.sleep(1)
            continue

        price = ws.price if ws.price else rest.get_price(symbol)

        if price is None:
            time.sleep(1)
            continue

        prices = ws.prices
        volumes = ws.volumes

        df = {
            "close": prices[-200:],
            "volume": volumes[-200:] if volumes else [1] * len(prices[-200:])
        }

        signal, score_val = score(df)

        with placeholder.container():
            run_dashboard(df, signal, score_val, ws)

        time.sleep(1)
