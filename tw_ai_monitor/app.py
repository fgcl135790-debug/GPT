import streamlit as st
import time

from data.fugle_ws import FugleWS
from data.fugle_rest import FugleREST
from core.engine_v2 import EngineV2
from ai.signal_v2 import SignalV2
from ui.dashboard_v3 import run_dashboard

st.set_page_config(layout="wide")

st.title("TW AI Monitor v3 Hybrid（WS + REST）")

api_key = st.text_input("Fugle API Key", type="password")
symbol = st.text_input("股票代碼", "2330")

start = st.button("開始監控")

if start:

    # ======================
    # 🔌 初始化資料源
    # ======================
    ws = FugleWS(api_key, symbol)
    ws.start()

    rest = FugleREST(api_key)

    engine = EngineV2()
    ai = SignalV2()

    placeholder = st.empty()

    # ======================
    # 🔁 主迴圈
    # ======================
    while True:

        try:

            # ======================
            # 🧠 1. 判斷 WS 是否活著
            # ======================
            ws_alive = (time.time() - ws.last_update) < 5

            # ======================
            # 📡 2. 取得價格（WS or REST）
            # ======================
            if ws_alive and len(ws.prices) > 0:
                price = ws.price
            else:
                price = rest.get_price(symbol)
                ws.prices.append(price)
                ws.volumes.append(1)

            # ======================
            # 📊 3. 建立 DF
            # ======================
            df = engine.build(ws.prices, ws.volumes)

            # ======================
            # 🤖 4. AI 判斷
            # ======================
            signal, score = ai.score(df)

            # ======================
            # 📺 5. 更新 UI
            # ======================
            with placeholder.container():
                run_dashboard(df, signal, score, ws)

            time.sleep(1)

        except Exception as e:
            st.write("ERROR:", e)
            time.sleep(2)
