import streamlit as st
import time

from data.fugle_rest import FugleREST
from core.engine_v2 import EngineV2
from ai.signal_v2 import SignalV2
from ui.dashboard_v3 import run_dashboard

st.set_page_config(layout="wide")

st.title("TW AI Monitor v3 Hybrid (REST Stable)")

api_key = st.text_input("Fugle API Key", type="password")
symbol = st.text_input("股票代碼", "2330")

if st.button("開始監控"):

    rest = FugleREST(api_key)

    engine = EngineV2()
    ai = SignalV2()

    placeholder = st.empty()

    while True:

        price = rest.get_price(symbol)

        if price is None:
            st.write("等待資料中...")
            time.sleep(1)
            continue

        df = engine.update(price)

        signal, score = ai.score(df)

        with placeholder.container():
            run_dashboard(df, signal, score, price)

        time.sleep(1)
