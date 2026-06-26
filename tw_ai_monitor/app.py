import streamlit as st
import requests
import time

# ================= UI =================
st.set_page_config(layout="wide", page_title="台股 AI 監控 V6.2")

st.title("📊 台股 AI 即時監控 V6.2（Fugle 原生修正版）")

api_key = st.text_input("API KEY", type="password")
stock = st.text_input("股票代碼", "2330")
refresh_sec = st.slider("更新頻率(秒)", 1, 10, 2)


# ================= API =================
def get_quote(stock_id):
    url = f"https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/{stock_id}"
    headers = {"X-API-KEY": api_key}

    r = requests.get(url, headers=headers)

    try:
        data = r.json()
    except:
        return {"error": "API 非 JSON"}

    # ❌ API錯誤
    if "error" in data:
        return {"error": data["error"]}

    # ===============================
    # ⭐ Fugle 新格式：直接就是 root
    # ===============================
    quote = data

    return {
        "name": quote.get("name"),
        "price": quote.get("lastPrice"),
        "change": quote.get("change"),
        "changePercent": quote.get("changePercent"),
        "volume": quote.get("total", {}).get("tradeVolume"),
        "bid": quote.get("bids", [{}])[0].get("price") if quote.get("bids") else None,
        "ask": quote.get("asks", [{}])[0].get("price") if quote.get("asks") else None,
        "bids": quote.get("bids", []),
        "asks": quote.get("asks", []),
    }


# ================= AI 判斷 =================
def ai_signal(price, bid, ask):
    if price is None:
        return "無資料", 0, "#999"

    if ask and price > ask:
        return "🚀 假突破偏多", 80, "#00c853"

    if bid and price < bid:
        return "📉 跌破偏空", 80, "#ff5252"

    return "⚖️ 盤整（觀望）", 50, "#ffc107"


# ================= MAIN =================
if api_key:

    q = get_quote(stock)

    if "error" in q:
        st.error(q["error"])
        st.stop()

    signal, score, color = ai_signal(q["price"], q["bid"], q["ask"])

    # ====== 上方資訊 ======
    st.markdown(f"""
    <div style="padding:20px;border-radius:12px;background:#111;">
        <div style="font-size:18px;color:#aaa;">
            {q['name']} ({stock})
        </div>

        <div style="font-size:52px;font-weight:800;color:{color}">
            {q['price']}
        </div>

        <div style="color:#ccc">
            漲跌：{q['change']} ({q['changePercent']}%)
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ====== 五檔（簡化專業版） ======
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🟢 買方")
        for b in q["bids"][:5]:
            st.write(f"{b['price']} | {b['size']}")

    with col2:
        st.subheader("🔴 賣方")
        for a in q["asks"][:5]:
            st.write(f"{a['price']} | {a['size']}")

    # ====== AI 訊號 ======
    st.subheader("🧠 AI 當沖判斷")
    st.markdown(f"## {signal}")
    st.progress(score / 100)

    # ====== 成交量 ======
    st.metric("成交量", q["volume"])

    # ====== 自動刷新 ======
    time.sleep(refresh_sec)
    st.rerun()

else:
    st.warning("請輸入 API KEY")
