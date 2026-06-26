import streamlit as st
import requests
import time

# ========== UI ==========
st.set_page_config(layout="wide", page_title="台股 AI 監控 V6.1")

st.title("📊 台股 AI 即時監控 V6.1（穩定修正版）")

FUGLE_KEY = st.text_input("API KEY", type="password")
stock = st.text_input("股票代碼", "2330")
refresh_sec = st.slider("更新頻率(秒)", 1, 10, 2)


# ========== API（防炸版） ==========
def get_fugle_quote(stock_id):
    url = f"https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/{stock_id}"
    headers = {"X-API-KEY": FUGLE_KEY}

    r = requests.get(url, headers=headers)

    try:
        raw = r.json()
    except:
        return {"error": "API 回傳非 JSON"}

    # ❗錯誤處理
    if "error" in raw:
        return {"error": raw["error"]}

    if "data" not in raw:
        return {"error": f"API 結構異常：{raw}"}

    data = raw["data"]

    # Fugle 有時會包 quote
    quote = data.get("quote", data)

    return {
        "name": data.get("symbolName", stock_id),
        "price": quote.get("lastPrice"),
        "change": quote.get("change"),
        "changePercent": quote.get("changePercent"),
        "bid": quote.get("bestBidPrice"),
        "ask": quote.get("bestAskPrice"),
        "volume": quote.get("totalTradeVolume")
    }


# ========== AI（簡化判斷） ==========
def ai_signal(price, bid, ask):
    if price is None:
        return "⚠️ 無資料", 0, "#999999"

    if price > ask:
        return "📈 偏多（突破）", 75, "#00c853"
    elif price < bid:
        return "📉 偏空（跌破）", 75, "#ff5252"
    else:
        return "⚖️ 盤整", 50, "#ffc107"


# ========== MAIN ==========
if FUGLE_KEY:

    data = get_fugle_quote(stock)

    # ❌ API錯誤直接顯示
    if "error" in data:
        st.error(data["error"])
        st.stop()

    signal, score, color = ai_signal(
        data["price"], data["bid"], data["ask"]
    )

    # ===== 上方資訊 =====
    st.markdown(f"""
    <div style="padding:20px;border-radius:15px;background:#111;">
        <div style="font-size:20px;color:#aaa;">
            {data['name']} ({stock})
        </div>

        <div style="font-size:48px;font-weight:800;color:{color}">
            {data['price']}
        </div>

        <div style="color:#ccc">
            漲跌：{data['change']} ({data['changePercent']}%)
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ===== 五檔 =====
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🟢 買方")
        st.write(f"Bid: {data['bid']}")

    with col2:
        st.subheader("🔴 賣方")
        st.write(f"Ask: {data['ask']}")

    # ===== AI訊號 =====
    st.subheader("🧠 AI 判斷")
    st.markdown(f"## {signal}")
    st.progress(score / 100)

    # ===== 成交量 =====
    st.write("成交量:", data["volume"])

    # ===== 自動刷新 =====
    time.sleep(refresh_sec)
    st.rerun()

else:
    st.warning("請輸入 Fugle API Key")
