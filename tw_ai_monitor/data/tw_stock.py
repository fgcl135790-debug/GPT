import requests
import pandas as pd

class TWStock:
    def get_data(self, stock_id):
        url = "https://api.finmindtrade.com/api/v4/data"
        
        params = {
            "dataset": "TaiwanStockPrice",
            "stock_id": stock_id,
            "limit": 100
        }

        r = requests.get(url, params=params)
        data = r.json()["data"]

        return pd.DataFrame(data)
