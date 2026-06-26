import streamlit as st
import requests

# =========================
# Page config
# =========================
st.set_page_config(layout="wide")

# =========================
# Sidebar
# =========================
st.sidebar.title("⚙️ 控制台")

api_key = st.sidebar.text_input("Fugle API Key", type="password")
symbol = st.sidebar.text_input("股票代碼", "2330")
refresh_sec = st.sidebar.slider("更新頻率（秒）", 1, 10, 2)

# =========================
# API
# =========================
def fetch_data():
    if not api_key:
        return None

    url = f"https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/{symbol}"
    headers = {"X-API-KEY": api_key.strip()}

    try:
        r = requests.get(url, headers=headers, timeout=10)
        return r.json() if r.status_code == 200 else None
    except:
        return None


# =========================
# 台股顏色（正確）
# =========================
def color(change):
    return "#e53935" if change > 0 else "#00c853"

def status(change):
    return "📈 上漲" if change > 0 else "📉 下跌"


# =========================
# UI container（避免重複）
# =========================
placeholder = st.empty()

data = fetch_data()

if not data:
    st.warning("請輸入 API KEY 或確認連線")
    st.stop()

# =========================
# 解析資料
# =========================
name = data.get("name", symbol)
price = data["lastPrice"]
change = data["change"]
pct = data["changePercent"]

bids = data["bids"]
asks = data["asks"]
total = data["total"]

# =========================
# render
# =========================
with placeholder.container():

    # ===== 上方資訊（已修正）=====
    st.markdown(
        f"""
        <div style="padding:18px;border-radius:12px;background:#111;margin-bottom:20px">
            <div style="font-size:18px;color:#aaa">
                ⚡ {name} ({symbol})
            </div>

            <div style="font-size:48px;font-weight:700;color:{color(change)}">
                {price}
            </div>

            <div style="font-size:14px;color:#ccc">
                {status(change)}  {change} / {pct:.2f}%
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # =========================
    # 五檔
    # =========================
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🟢 買方")
        st.markdown("價格　　張數")

        for b in bids:
            st.markdown(
                f"{b['price']}　　<span style='color:#00c853'>{b['size']}</span>",
                unsafe_allow_html=True
            )

    with col2:
        st.markdown("### 🔴 賣方")
        st.markdown("張數　　價格")

        for a in asks:
            st.markdown(
                f"<span style='color:#e53935'>{a['size']}</span>　　{a['price']}",
                unsafe_allow_html=True
            )

    # =========================
    # 成交資訊（已修 bug）
    # =========================
    st.markdown("### 📦 成交資訊")

    c1, c2, c3 = st.columns(3)

    c1.metric("成交金額", f"{total['tradeValue']:,}")
    c2.metric("成交張數", f"{total['tradeVolume']:,}")
    c3.metric("成交筆數", f"{total['transaction']:,}")
