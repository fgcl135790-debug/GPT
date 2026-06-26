import requests
import pandas as pd

class TWStock:

    def get_data(self, stock_id, token):

        url = "https://api.finmindtrade.com/api/v4/data"

        params = {
            "dataset": "TaiwanStockPrice",
            "stock_id": stock_id,
            "token": token,
            "limit": 100
        }

        r = requests.get(url, params=params)
        result = r.json()

        if "data" not in result:
            return pd.DataFrame({
                "error": [result]
            })

        return pd.DataFrame(result["data"])
