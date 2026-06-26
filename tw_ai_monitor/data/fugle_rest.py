import requests

class FugleREST:

    def __init__(self, api_key):
        self.api_key = api_key

    def get_price(self, symbol):

        url = f"https://api.fugle.tw/marketdata/v1.0/stock/quote/{symbol}"

        headers = {
            "X-API-KEY": self.api_key
        }

        try:
            res = requests.get(url, headers=headers)
            data = res.json()

            return data["data"]["quote"]["tradePrice"]

        except Exception as e:
            print("REST error:", e)
            return None
