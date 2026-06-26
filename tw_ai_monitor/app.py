import streamlit as st
from data.tw_stock import TWStock
from core.analyzer import Analyzer

st.title("🇹🇼 台股 AI 監控系統")

stock_id = st.text_input("股票代碼（例如 2330）", "2330")

data = TWStock()
analyzer = Analyzer()

if st.button("開始監控"):

    df = data.get_data(stock_id)
    result = analyzer.run(df)

    st.subheader("AI 判斷")
    st.write(result["ai_signal"])

    st.subheader("均線")
    st.write("MA5:", result["ma5"])
    st.write("MA20:", result["ma20"])

    st.line_chart(df["close"])
