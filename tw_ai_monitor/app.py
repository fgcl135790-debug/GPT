import streamlit as st
import requests
import pandas as pd

# =====================
# CONFIG
# =====================
st.set_page_config(layout="wide", page_title="AI 看盤 V7")

FUGLE_URL = "https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote"

# =====================
# API
# =====================
def get_quote(stock, api_key):
    headers = {"X-API-KEY": api_key}
    r = requests.get(f"{FUGLE_URL}/{stock}", headers=headers)
    data = r.json()

    # === SAFE PARSE（避免你之前 KeyError）===
    try:
        d = data["data"]
    except:
        return None

    return {
        "symbol": d.get("symbol"),
        "name": d.get("name"),
        "price": d.get("closePrice"),
        "change": d.get("change"),
        "changePercent": d.get("changePercent"),
        "open": d.get("openPrice"),
        "high": d.get("highPrice"),
        "low": d.get("lowPrice"),
        "volume": d.get("total").get("tradeVolume") if d.get("total") else 0,
        "bid": d.get("orderBook", {}).get("bids", []),
        "ask": d.get("orderBook", {}).get("asks", []),
        "vwap": d.get("total").get("avgPrice") if d.get("total") else 0,
    }

# =====================
# AI SIGNAL ENGINE（簡化版）
# =====================
def ai_signal(q):
    if not q:
        return "無資料", 0

    score = 50

    # VWAP logic
    if q["price"] > q["vwap"]:
        score += 15
    else:
        score -= 15

    # momentum
    if q["change"] > 0:
        score += 10
    else:
        score -= 10

    if score >= 65:
        return "📈 偏多", score
    elif score <= 35:
        return "📉 偏空", score
    else:
        return "⚖️ 盤整", score

# =====================
# UI STYLE（關鍵）
# =====================
st.markdown("""
<style>
/* 左側控制台 */
section[data-testid="stSidebar"] {
    background-color:#0e1117;
}

/* 卡片 */
.card {
    background:#161b22;
    padding:16px;
    border-radius:12px;
    margin-bottom:12px;
}

/* 五檔表 */
.book {
    display:flex;
    justify-content:space-between;
}

/* 買賣顏色 */
.buy {color:#00d084;}
.sell {color:#ff4d4d;}
</style>
""", unsafe_allow_html=True)

# =====================
# SIDEBAR
# =====================
with st.sidebar:
    st.title("⚙️ 控制台")

    api = st.text_input("API KEY", type="password")
    stock = st.text_input("股票代碼", "2330")
    refresh = st.slider("更新秒數", 1, 10, 2)

# =====================
# MAIN
# =====================
st.title(f"⚡ {stock} AI 即時監控 V7")

if api:
    q = get_quote(stock, api)

    if q:

        signal, score = ai_signal(q)

        # ===== TOP CARD =====
        st.markdown(f"""
        <div class="card">
            <h2>{q['name']} ({q['symbol']})</h2>
            <h1 style="color:#00ff99">{q['price']}</h1>
            <p>漲跌: {q['change']} ({q['changePercent']}%)</p>
        </div>
        """, unsafe_allow_html=True)

        # ===== SIGNAL =====
        st.markdown(f"""
        <div class="card">
            <h3>AI 當沖判斷</h3>
            <h2>{signal}</h2>
            <p>Score: {score}</p>
        </div>
        """, unsafe_allow_html=True)

        # ===== ORDER BOOK（三竹風格）=====
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🟢 買方")
            for b in q["bid"][:5]:
                st.markdown(f"<div class='buy'>{b['price']} | {b['size']}</div>", unsafe_allow_html=True)

        with col2:
            st.subheader("🔴 賣方")
            for a in q["ask"][:5]:
                st.markdown(f"<div class='sell'>{a['price']} | {a['size']}</div>", unsafe_allow_html=True)

        # ===== STATS =====
        st.markdown("### 📊 成交資訊")
        c1, c2, c3 = st.columns(3)

        c1.metric("VWAP", q["vwap"])
        c2.metric("成交量", q["volume"])
        c3.metric("現價", q["price"])

else:
    st.warning("請輸入 API KEY")
