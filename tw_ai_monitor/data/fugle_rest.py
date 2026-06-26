import requests

BASE_URL = "https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote"

def get_price(symbol: str, api_key: str):

    url = f"{BASE_URL}?symbolId={symbol}"

    headers = {
        "X-API-KEY": api_key
    }

    try:
        res = requests.get(url, headers=headers, timeout=5)
        data = res.json()

        # 🔥 debug（一定要保留）
        print("REST RAW:", data)

        # ❗防 error response
        if "data" not in data:
            return None

        quote = data["data"].get("quote", {})
        price = quote.get("tradePrice")

        return price

    except Exception as e:
        print("REST ERROR:", e)
        return None
