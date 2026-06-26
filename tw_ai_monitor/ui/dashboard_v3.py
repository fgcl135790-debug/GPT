import streamlit as st
import plotly.graph_objects as go

def run_dashboard(df, signal, score, ws):

    st.title("TW AI Monitor v3 Stable (REST)")

    fig = go.Figure()

    fig.add_trace(go.Scatter(y=df["close"], name="Price"))

    st.plotly_chart(fig, use_container_width=True)

    col1, col2, col3 = st.columns(3)

    col1.metric("即時價格", ws.price if ws.price else "N/A")
    col2.metric("AI訊號", signal)
    col3.metric("強度", f"{score}/100")

    st.bar_chart(df["volume"])
