import requests
import pandas as pd

def get_snapshot(api_key, symbol):

    url = f"https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/{symbol}"

    headers = {
        "X-API-KEY": api_key
    }

    try:
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()

        # ======================
        # 防呆（避免 KeyError）
        # ======================
        if "data" not in data:
            return None, None

        quote = data["data"].get("quote", {})
        price = quote.get("tradePrice", None)

        # 模擬 K 線（因為 free API 沒 full OHLC）
        df = pd.DataFrame({
            "close": [price] if price else [],
            "volume": [0]
        })

        return df, price

    except Exception as e:
        print("REST ERROR:", e)
        return None, None
