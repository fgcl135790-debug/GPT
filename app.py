import streamlit as st
from core.data_provider import DataProvider
from core.engine import Engine
from models.predictor import Predictor

st.title("📊 Trading System v2")

provider = DataProvider()
engine = Engine()
predictor = Predictor()

symbol = st.text_input("股票代碼", "2330")

if st.button("開始"):
    data = provider.get(symbol)

    signal = predictor.predict(data)
    result = engine.simulate(data, signal)

    st.write(signal)
    st.write(result)
