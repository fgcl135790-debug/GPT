import streamlit as st
import plotly.graph_objects as go

def run_dashboard(df, signal, score, ws):

    st.title("🇹🇼 台股 AI 監控系統 v3（專業看盤版）")

    # =====================
    # 📊 上層：價格 + 均線
    # =====================
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        y=df["close"],
        name="Price"
    ))

    if "ema5" in df.columns:
        fig.add_trace(go.Scatter(y=df["ema5"], name="EMA5"))
        fig.add_trace(go.Scatter(y=df["ema20"], name="EMA20"))
        fig.add_trace(go.Scatter(y=df["ema60"], name="EMA60"))

    if "vwap" in df.columns:
        fig.add_trace(go.Scatter(y=df["vwap"], name="VWAP"))

    st.plotly_chart(fig, use_container_width=True)

    # =====================
    # 🤖 中層 AI
    # =====================
    col1, col2, col3 = st.columns(3)

    col1.metric("即時價格", ws.price)
    col2.metric("AI訊號", signal)
    col3.metric("強度", f"{score}/100")

    # =====================
    # 📊 Volume
    # =====================
    st.bar_chart(df["volume"])
