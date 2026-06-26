import streamlit as st
from data.fugle_rest import get_snapshot
from ai.signal_v2 import score
from ui.dashboard_v3 import run_dashboard

st.set_page_config(page_title="TW AI Monitor", layout="wide")

st.title("TW AI Monitor v3 Stable (REST Only)")

api_key = st.text_input("Fugle API Key", type="password")
symbol = st.text_input("股票代碼", value="2330")

if st.button("開始監控"):

    # =========================
    # 🔥 安全初始化（重點）
    # =========================
    df = None
    price = None

    # =========================
    # REST 抓資料
    # =========================
    try:
        df, price = get_snapshot(api_key, symbol)
    except Exception as e:
        st.error(f"API 例外錯誤: {e}")
        st.stop()

    # =========================
    # 🔥 防炸核心（修 NameError）
    # =========================
    if df is None or len(df) == 0:
        st.error("無法取得資料（REST失敗 or API無回應）")
        st.stop()

    # =========================
    # AI
    # =========================
    signal, score_val = score(df)

    ws = type("obj", (), {"price": price})

    # =========================
    # UI
    # =========================
    run_dashboard(df, signal, score_val, ws)
