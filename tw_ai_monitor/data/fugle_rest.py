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
        data = r.json()

        return data["data"]["quote"]["tradePrice"]
