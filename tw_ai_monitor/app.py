import streamlit as st
import requests
import time

# ========== CONFIG ==========
st.set_page_config(layout="wide", page_title="AI 台股監控 V6")

FUGLE_KEY = st.text_input("API KEY", type="password")
stock = st.text_input("股票代碼", "2330")
refresh_sec = st.slider("更新頻率(秒)", 1, 10, 2)

# ========== API ==========
def get_fugle_quote(stock_id):
    url = f"https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/{stock_id}"
    headers = {"X-API-KEY": FUGLE_KEY}

    r = requests.get(url, headers=headers)
    data = r.json()["data"]

    return {
        "name": data["symbolName"],
        "price": data["lastPrice"],
        "change": data["change"],
        "changePercent": data["changePercent"],
        "bid": data["bestBidPrice"],
        "ask": data["bestAskPrice"],
        "volume": data["totalTradeVolume"]
    }


# ========== AI LOGIC ==========
def ai_signal(price, bid, ask):
    if price > bid and price > ask:
        return "📈 可偏多", 75, "#00c853"
    elif price < bid:
        return "📉 可偏空", 75, "#ff5252"
    else:
        return "⚖️ 盤整", 50, "#ffc107"


# ========== UI ==========
st.title("📊 台股 AI 即時監控 V6（實盤版）")

if FUGLE_KEY:
    data = get_fugle_quote(stock)

    signal, score, color = ai_signal(data["price"], data["bid"], data["ask"])

    # ====== 上方資訊卡 ======
    st.markdown(f"""
    <div style="padding:20px;border-radius:15px;background:#111;">
        <div style="font-size:22px;color:#aaa;">{data['name']} ({stock})</div>

        <div style="font-size:48px;font-weight:800;color:{color}">
            {data['price']}
        </div>

        <div style="font-size:16px;color:#ccc">
            漲跌：{data['change']} ({data['changePercent']}%)
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ====== 五檔（簡化版） ======
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🟢 買方")
        st.write(f"買價：{data['bid']}")

    with col2:
        st.subheader("🔴 賣方")
        st.write(f"賣價：{data['ask']}")

    # ====== AI 訊號 ======
    st.subheader("🧠 AI 判斷")
    st.markdown(f"### {signal}")
    st.progress(score / 100)

    # ====== 成交量 ======
    st.subheader("📦 成交量")
    st.write(data["volume"])

    # ====== auto refresh ======
    time.sleep(refresh_sec)
    st.rerun()

else:
    st.warning("請輸入 Fugle API Key")
