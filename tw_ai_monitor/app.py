import streamlit as st
import requests

# ======================
# CONFIG
# ======================
st.set_page_config(
    page_title="台股 AI 即時監控 V7.3",
    layout="wide"
)

# ======================
# SIDEBAR
# ======================
st.sidebar.title("⚙️ 控制台")

api_key = st.sidebar.text_input("API KEY", type="password")
stock = st.sidebar.text_input("股票代碼", "2330")
refresh = st.sidebar.slider("更新秒數", 1, 10, 2)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🧪 Debug")
st.sidebar.write("API:", bool(api_key))
st.sidebar.write("Stock:", stock)

# ======================
# API（🔥已修正 Fugle schema）
# ======================
def get_quote(stock, api_key):
    url = f"https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/{stock}"

    try:
        r = requests.get(
            url,
            headers={"X-API-KEY": api_key},
            timeout=5
        )

        j = r.json()

        # 🔥 Fugle 新版：root 就是資料
        d = j

        return {
            "name": d.get("name", "-"),
            "symbol": d.get("symbol", stock),
            "price": d.get("closePrice") or d.get("lastPrice", 0),
            "change": d.get("change", 0),
            "changePercent": d.get("changePercent", 0),
            "vwap": d.get("avgPrice", 0),
            "volume": d.get("tradeVolume", 0),
            "high": d.get("highPrice", 0),
            "low": d.get("lowPrice", 0),
            "open": d.get("openPrice", 0),
            "bids": d.get("bids", []),
            "asks": d.get("asks", []),
        }

    except Exception as e:
        return {"error": str(e)}

# ======================
# AI 判斷（VWAP + momentum）
# ======================
def ai_signal(data):
    score = 50

    if not data:
        return "⚖️ 無資料", 50

    if data["price"] > data["vwap"]:
        score += 15
    else:
        score -= 15

    if data["change"] > 0:
        score += 10
    else:
        score -= 10

    spread = len(data["bids"]) - len(data["asks"])
    if spread > 0:
        score += 5
    else:
        score -= 5

    if score >= 65:
        return "📈 偏多（可做多）", score
    elif score <= 35:
        return "📉 偏空（可做空）", score
    else:
        return "⚖️ 盤整（觀望）", score

# ======================
# ALWAYS RENDER UI
# ======================
st.title("⚡ 台股 AI 即時監控 V7.3（穩定版）")

# ======================
# FETCH DATA（安全模式）
# ======================
data = None
error = None

if api_key and stock:
    result = get_quote(stock, api_key)

    if "error" in result:
        error = result["error"]
    else:
        data = result
else:
    st.warning("請輸入 API KEY + 股票代碼")

# ======================
# ERROR BLOCK（不會中斷 UI）
# ======================
if error:
    st.error("API 錯誤")
    st.json(error)

# ======================
# MAIN DASHBOARD
# ======================
if data:

    signal, score = ai_signal(data)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("現價", data["price"])
        st.metric("漲跌", data["change"])

    with col2:
        st.metric("VWAP", data["vwap"])
        st.metric("成交量", data["volume"])

    with col3:
        st.metric("高點", data["high"])
        st.metric("低點", data["low"])

    st.markdown("## 🤖 AI 當沖判斷")
    st.success(f"{signal} ｜ Score：{score}")

    # ======================
    # order book（簡化版）
    # ======================
    st.markdown("## 📊 買賣盤")

    colA, colB = st.columns(2)

    with colA:
        st.markdown("### 🟢 買方")
        for b in data["bids"][:5]:
            st.write(f"{b.get('price')} | {b.get('size')}")

    with colB:
        st.markdown("### 🔴 賣方")
        for a in data["asks"][:5]:
            st.write(f"{a.get('price')} | {a.get('size')}")

else:
    st.info("等待資料中...")

# ======================
# FOOTER DEBUG
# ======================
st.sidebar.markdown("---")
st.sidebar.write("STATE")
st.sidebar.write("data:", data is not None)
st.sidebar.write("error:", error is not None)
