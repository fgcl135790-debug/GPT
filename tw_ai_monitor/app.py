import streamlit as st
from data.fugle_rest import get_snapshot
from ai.signal_v2 import score as ai_score

st.set_page_config(page_title="TW AI Monitor v3 Stable", layout="wide")

st.title("TW AI Monitor v3 Stable")

api_key = st.text_input("Fugle API Key", type="password")
symbol = st.text_input("股票代碼", value="2330")

df = None
price = None
signal = "WAIT"
score_val = 0

if st.button("開始監控"):

    df, price = get_snapshot(api_key, symbol)

    # 🚨 1. API 失敗直接擋掉
    if df is None:
        st.error("❌ 無法取得資料（df = None）")
        st.stop()

    if len(df) == 0:
        st.error("❌ df 是空的")
        st.stop()

    # 🤖 AI 計算
    signal, score_val = ai_score(df)

    # ======================
    # UI 顯示區（安全版）
    # ======================

    col1, col2, col3 = st.columns(3)
    col1.metric("價格", price if price else "N/A")
    col2.metric("訊號", signal)
    col3.metric("強度", f"{score_val}/100")

    st.divider()

    # 📊 dataframe（🔥關鍵修復）
    if df is not None and len(df) > 0:
        st.dataframe(df.tail(10))
    else:
        st.warning("沒有資料可顯示")
