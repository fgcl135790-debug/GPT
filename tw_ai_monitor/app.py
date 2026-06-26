import streamlit as st
import requests
import time

st.set_page_config(page_title="TW AI Monitor v3.1", layout="wide")

# ================= STYLE =================
st.markdown("""
<style>
.big { font-size: 44px; font-weight: 700; }
.up { color: #e74c3c; }   /* 台股紅 */
.down { color: #2ecc71; } /* 台股綠 */

.card {
    padding: 16px;
    border-radius: 14px;
    background: #111;
    margin-bottom: 12px;
}

.title {
    font-size: 22px;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)


# ================= SIDEBAR =================
with st.sidebar:
    st.title("⚙️ 控制台")

    api_key = st.text_input("Fugle API Key", type="password")
    symbol = st.text_input("股票代碼", value="2330")
    refresh = st.slider("更新頻率(秒)", 1, 10, 2)

    st.divider()
    st.write("Auto Refresh：ON")


# ================= API =================
def get_data(symbol, key):
    url = f"https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/{symbol}"
    headers = {"X-API-KEY": key}
    r = requests.get(url, headers=headers, timeout=10)
    return r.json()


# ================= MAIN =================
st.title(f"📊 台股看盤系統 {symbol}")

placeholder = st.empty()

while True:

    if not api_key:
        st.warning("請輸入 API KEY")
        time.sleep(1)
        continue

    try:
        data = get_data(symbol, api_key)

        price = data["lastPrice"]
        change = data["change"]
        pct = data["changePercent"]

        up = change >= 0
        color = "up" if up else "down"
        status = "📈 上漲" if up else "📉 下跌" if change < 0 else "⚪ 盤整"

        with placeholder.container():

            # ====== 股票資訊 ======
            st.markdown(f"""
            <div class="card">
                <div class="title">{data['name']} ({symbol})</div>
                <div>{status}</div>
                <div class="big {color}">{price}</div>
                <div>漲跌：{change} / {pct}%</div>
            </div>
            """, unsafe_allow_html=True)

            col1, col2 = st.columns(2)

            # ====== 五檔 ======
            with col1:
                st.subheader("📉 買方")
                bids = data.get("bids", [])[:5]
                for b in bids:
                    st.write(f"{b['price']} | {b['size']}")

            with col2:
                st.subheader("📈 賣方")
                asks = data.get("asks", [])[:5]
                for a in asks:
                    st.write(f"{a['price']} | {a['size']}")

            # ====== 成交量（修正重點） ======
            total = data.get("total", {})

            st.markdown("### 📦 成交資訊")

            col3, col4, col5 = st.columns(3)

            col3.metric("成交金額", f"{total.get('tradeValue',0):,}")
            col4.metric("成交量", f"{total.get('tradeVolume',0):,}")
            col5.metric("成交筆數", f"{total.get('transaction',0):,}")

    except Exception as e:
        st.error(e)

    time.sleep(refresh)
