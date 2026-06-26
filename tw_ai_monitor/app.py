import streamlit as st
from data.fugle_rest import get_snapshot
from ai.signal_v2 import score
from ui.dashboard_v3 import run_dashboard

st.set_page_config(page_title="TW AI Monitor", layout="wide")

st.title("TW AI Monitor v3 Stable (REST Only)")

api_key = st.text_input("Fugle API Key", type="password")
symbol = st.text_input("股票代碼", value="2330")

if st.button("開始監控"):

    if not api_key:
        st.error("請輸入 API Key")
        st.stop()

    # ======================
    # REST 抓資料
    # ======================
    df, price = get_snapshot(api_key, symbol)

if df is None or len(df) == 0:
    st.error("無法取得資料（請看 terminal log）")
    st.stop()

    # ======================
    # AI 分數
    # ======================
    signal, score_val = score(df)

    # ======================
    # UI
    # ======================
    ws = type("obj", (), {"price": price})

    run_dashboard(df, signal, score_val, ws)
