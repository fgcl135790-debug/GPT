import streamlit as st
import requests
import time

st.set_page_config(page_title="TW Monitor", layout="wide")

# ================= CSS（仿三竹風格） =================
st.markdown("""
<style>
.big {
    font-size: 46px;
    font-weight: 800;
}

.up { color: #e74c3c; }   /* 台股紅 */
.down { color: #2ecc71; } /* 台股綠 */

.card {
    background: #111;
    padding: 18px;
    border-radius: 14px;
    margin-bottom: 12px;
}

.bid {
    color: #2ecc71;
    font-weight: 600;
}

.ask {
    color: #e74c3c;
    font-weight: 600;
}

.small {
    opacity: 0.8;
    font-size: 13px;
}
</style>
""", unsafe_allow_html=True)


# ================= SIDEBAR =================
with st.sidebar:
    st.title("⚙️ 控制台")

    api_key = st.text_input("Fugle API Key", type="password")
    symbol = st.text_input("股票代碼", value="2330")
    refresh = st.slider("更新頻率", 1, 10, 2)

    st.write("Auto Refresh: ON")


# ================= API =================
def fetch(symbol, key):
    url = f"https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/{symbol}"
    headers = {"X-API-KEY": key}
    return requests.get(url, headers=headers, timeout=10).json()


# ================= FORMAT =================
def format_num(n):
    if n >= 10000:
        return f"{n/10000:.1f}萬"
    return f"{n:,}"


# ================= MAIN =================
placeholder = st.empty()

while True:

    if not api_key:
        st.warning("請輸入 API KEY")
        time.sleep(1)
        continue

    try:
        d = fetch(symbol, api_key)

        price = d["lastPrice"]
        change = d["change"]
        pct = d["changePercent"]

        up = change >= 0
        color = "up" if up else "down"
        status = "📈 上漲" if change > 0 else "📉 下跌" if change < 0 else "⚪ 盤整"

        with placeholder.container():

            # ================= 股票資訊（移除標題） =================
            st.markdown(f"""
            <div class="card">
                <div style="font-size:18px;">{d['name']} ({symbol})</div>
                <div>{status}</div>
                <div class="big {color}">{price}</div>
                <div>漲跌 {change} / {pct}%</div>
            </div>
            """, unsafe_allow_html=True)

            col1, col2 = st.columns(2)

            # ================= 買方（仿三竹） =================
            with col1:
                st.subheader("🟢 買方")

                for i, b in enumerate(d.get("bids", [])[:5]):

                    price_cls = "bid"
                    st.markdown(
                        f"{b['price']} <span class='{price_cls}'>| {format_num(b['size'])}</span>",
                        unsafe_allow_html=True
                    )

            # ================= 賣方 =================
            with col2:
                st.subheader("🔴 賣方")

                for i, a in enumerate(d.get("asks", [])[:5]):

                    price_cls = "ask"
                    st.markdown(
                        f"{a['price']} <span class='{price_cls}'>| {format_num(a['size'])}</span>",
                        unsafe_allow_html=True
                    )

            # ================= 成交資訊（修正重點） =================
            t = d.get("total", {})

            st.markdown("### 📦 成交資訊")

            c1, c2, c3 = st.columns(3)

            c1.metric("成交金額", format_num(t.get("tradeValue", 0)))
            c2.metric("成交張數", format_num(t.get("tradeVolume", 0)))
            c3.metric("成交筆數", format_num(t.get("transaction", 0)))

    except Exception as e:
        st.error(e)

    time.sleep(refresh)
