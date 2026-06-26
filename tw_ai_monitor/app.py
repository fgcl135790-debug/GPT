import streamlit as st
import requests

st.set_page_config(layout="wide", page_title="AI 監控 V7.2")

# ======================
# DEBUG PANEL（超重要）
# ======================
st.sidebar.title("⚙️ 控制台")

api_key = st.sidebar.text_input("API KEY", type="password")
stock = st.sidebar.text_input("股票代碼", "2330")
refresh = st.sidebar.slider("更新秒數", 1, 10, 2)

st.sidebar.markdown("### 🧪 Debug")
st.sidebar.write("API:", bool(api_key))
st.sidebar.write("Stock:", stock)

# ======================
# API
# ======================
def get_quote(stock, api_key):
    url = f"https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/{stock}"
    try:
        r = requests.get(url, headers={"X-API-KEY": api_key}, timeout=5)
        j = r.json()

        # 🔥 永遠不要讓 exception crash UI
        if "data" not in j:
            return {"error": j}

        d = j["data"]

        return {
            "name": d.get("name", "-"),
            "price": d.get("closePrice", 0),
            "change": d.get("change", 0),
            "vwap": (d.get("total") or {}).get("avgPrice", 0),
            "volume": (d.get("total") or {}).get("tradeVolume", 0),
        }

    except Exception as e:
        return {"error": str(e)}

# ======================
# AI
# ======================
def ai(stock_data):
    if not stock_data:
        return "無資料", 50

    score = 50

    if stock_data["price"] > stock_data["vwap"]:
        score += 15
    else:
        score -= 15

    if stock_data["change"] > 0:
        score += 10
    else:
        score -= 10

    if score > 65:
        return "📈 做多", score
    elif score < 35:
        return "📉 做空", score
    else:
        return "⚖️ 盤整", score

# ======================
# ALWAYS RENDER HEADER
# ======================
st.title("⚡ 2330 AI 即時監控 V7.2")

# ======================
# SAFE FLOW（重點）
# ======================
data = None
error = None

if api_key and stock:
    result = get_quote(stock, api_key)

    if isinstance(result, dict) and "error" in result:
        error = result["error"]
    else:
        data = result
else:
    st.warning("請輸入 API KEY + 股票代碼")

# ======================
# 🔥 NEVER BLANK SCREEN
# ======================
if error:
    st.error("API 錯誤")
    st.json(error)

# ======================
# UI ALWAYS SHOW
# ======================
if data:

    signal, score = ai(data)

    st.markdown("## 即時價格")
    st.metric("現價", data["price"])
    st.metric("VWAP", data["vwap"])
    st.metric("漲跌", data["change"])

    st.markdown("## AI 判斷")
    st.success(f"{signal} ｜ Score {score}")

else:
    st.info("等待資料中（請確認 API KEY）")

# ======================
# 🔥 FORCE DEBUG FOOTER
# ======================
st.sidebar.markdown("---")
st.sidebar.write("STATE CHECK:")
st.sidebar.write("data:", data is not None)
st.sidebar.write("error:", error is not None)
