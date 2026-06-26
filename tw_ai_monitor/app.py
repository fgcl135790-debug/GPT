import streamlit as st
from data.fugle_rest import get_snapshot
from ai.signal_v2 import score as ai_score

st.title("TW AI Monitor v3 Stable")

api_key = st.text_input("Fugle API Key", type="password")
symbol = st.text_input("股票代碼", value="2330")

if st.button("開始監控"):

    df, price = get_snapshot(api_key, symbol)

    # 🚨 最重要防炸點
    if df is None:
        st.error("❌ REST 沒拿到資料（df = None）")
        st.stop()

    if len(df) == 0:
        st.error("❌ df 是空的")
        st.stop()

    signal, score_val = ai_score(df)

    col1, col2, col3 = st.columns(3)
    col1.metric("價格", price if price else "N/A")
    col2.metric("訊號", signal)
    col3.metric("強度", f"{score_val}/100")

    st.dataframe(df.tail())
