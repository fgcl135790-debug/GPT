import requests


class FugleREST:

    def __init__(self, api_key):
        self.api_key = api_key

    def get_price(self, symbol):

        url = f"https://api.fugle.tw/marketdata/v1.0/stock/quote/{symbol}"

        headers = {
            "X-API-KEY": self.api_key
        }

        r = requests.get(url, headers=headers)

        try:
            data = r.json()

            # 🔥 debug（一定要先看一次）
            print("REST RAW:", data)

            # ======================
            # 🧠 Fugle 常見結構修正
            # ======================

            # 有些版本是這個
            if "data" in data:
                return data["data"]["quote"]["tradePrice"]

            # 有些版本是直接 quote
            if "quote" in data:
                return data["quote"]["tradePrice"]

            # fallback
            return None

        except Exception as e:
            print("REST error:", e)
            return None
