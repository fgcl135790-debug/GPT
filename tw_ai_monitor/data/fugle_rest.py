import requests
import pandas as pd

def get_snapshot(api_key, symbol):

    url = f"https://api.fugle.tw/marketdata/v1.0/stock/quote/{symbol}"

    headers = {
        "X-API-KEY": api_key
    }

    try:
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()

        # =========================
        # 防呆 1：API 失敗
        # =========================
        if not isinstance(data, dict):
            return None, None

        if "data" not in data:
            print("API回傳：", data)
            return None, None

        quote = data["data"].get("quote", {})

        price = quote.get("tradePrice") or quote.get("close")

        if price is None:
            return None, None

        # =========================
        # 模擬 dataframe（免費版沒K線）
        # =========================
        df = pd.DataFrame({
            "close": [price],
            "volume": [0]
        })

        return df, price

    except Exception as e:
        print("REST ERROR:", e)
        return None, None
