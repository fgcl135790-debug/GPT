import streamlit as st
import requests

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="AI 即時監控 V7.1",
    layout="wide"
)

# =========================
# API CONFIG
# =========================
FUGLE_URL = "https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote"

# =========================
# DATA FETCH (SAFE)
# =========================
def get_quote(stock, api_key):
    try:
        headers = {"X-API-KEY": api_key}
        r = requests.get(f"{FUGLE_URL}/{stock}", headers=headers, timeout=5)

        data = r.json()

        if "data" not in data:
            return None

        d = data["data"]

        return {
            "symbol": d.get("symbol", stock),
            "name": d.get("name", "-"),
            "price": d.get("closePrice", 0),
            "change": d.get("change", 0),
            "changePercent": d.get("changePercent", 0),
            "vwap": (d.get("total") or {}).get("avgPrice", 0),
            "volume": (d.get("total") or {}).get("tradeVolume", 0),
            "bid": (d.get("orderBook") or {}).get("bids", []),
            "ask": (d.get("orderBook") or {}).get("asks", []),
        }

    except Exception as e:
        return {"error": str(e)}

# =========================
# AI SIGNAL ENGINE
# =========================
def ai_signal(q):
    if not q:
        return "無訊號", 50

    score = 50

    if q["price"] > q["vwap"]:
        score += 15
    else:
        score -= 15

    if q["change"] > 0:
        score += 10
    else:
        score -= 10

    if score >= 65:
        return "📈 偏多（可做多）", score
    elif score <= 35:
        return "📉 偏空（可放空）", score
    else:
        return "⚖️ 盤整（觀望）", score

# =========================
# UI STYLE
# =========================
st.markdown("""
<style>
.block {
    background:#111827;
    padding:16px;
    border-radius:12px;
    margin-bottom:12px;
}

.buy { color:#00ff99; }
.sell { color:#ff4d4d; }

.big {
    font-size:40px;
    font-weight:800;
}
</style>
""", unsafe_allow_html=True)

# =========================
# SIDEBAR
# =========================
with st.sidebar:
    st.title("⚙️ 控制台")

    api_key = st.text_input("API KEY", type="password")
    stock = st.text_input("股票代碼", "2330")
    refresh = st.slider("更新秒數", 1, 10, 2)

# =========================
# MAIN
# =========================
st.title("⚡ 台股 AI 即時監控 V7.1")

q = None
error = None

if api_key and stock:
    result = get_quote(stock, api_key)

    if isinstance(result, dict) and "error" in result:
        error = result["error"]
    else:
        q = result
else:
    st.warning("請輸入 API KEY + 股票代碼")

# =========================
# ERROR DISPLAY（不會空白）
# =========================
if error:
    st.error(f"API 錯誤：{error}")

elif q:

    signal, score = ai_signal(q)

    # ================= TOP =================
    st.markdown(f"""
    <div class="block">
        <div style="font-size:18px;">{q['name']} ({q['symbol']})</div>
        <div class="big" style="color:#00ff99">{q['price']}</div>
        <div>漲跌：{q['change']} ({q['changePercent']}%)</div>
    </div>
    """, unsafe_allow_html=True)

    # ================= AI =================
    st.markdown(f"""
    <div class="block">
        <h3>🤖 AI 當沖判斷</h3>
        <h2>{signal}</h2>
        <p>Score：{score}</p>
    </div>
    """, unsafe_allow_html=True)

    # ================= STATS =================
    c1, c2, c3 = st.columns(3)
    c1.metric("VWAP", q["vwap"])
    c2.metric("成交量", q["volume"])
    c3.metric("現價", q["price"])

    st.divider()

    # ================= ORDER BOOK =================
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🟢 買方")
        bids = q.get("bid", [])
        if bids:
            for b in bids[:5]:
                st.markdown(f"<div class='buy'>{b['price']} | {b['size']}</div>", unsafe_allow_html=True)
        else:
            st.write("無買盤")

    with col2:
        st.subheader("🔴 賣方")
        asks = q.get("ask", [])
        if asks:
            for a in asks[:5]:
                st.markdown(f"<div class='sell'>{a['price']} | {a['size']}</div>", unsafe_allow_html=True)
        else:
            st.write("無賣盤")
