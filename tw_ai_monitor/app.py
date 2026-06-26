import streamlit as st
from data.tw_stock import TWStock

st.title("TW 台股 AI 監控系統")

stock_id = st.text_input("股票代碼", "2330")

token = st.text_input("FinMind API Token", type="password")

if st.button("開始監控"):

    data = TWStock()
    df = data.get_data(stock_id, token)

    st.write(df)
