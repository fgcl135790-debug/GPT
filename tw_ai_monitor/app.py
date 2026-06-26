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

    # 🔥 用 Streamlit 安全迴圈（不要 while True）
    for i in range(1000):

        # 👉 防止還沒資料就報錯
        if len(ws.prices) < 20:
            placeholder.write(f"等待資料中... ({len(ws.prices)})")
            time.sleep(1)
            continue

        # 📊 建立資料
        df = engine.build(ws.prices, ws.volumes)

        # 🤖 AI 判斷
        signal, score = ai.score(df)

        # 📈 更新畫面
        with placeholder.container():
            run_dashboard(df, signal, score, ws)

        time.sleep(1)
