import requests
import pandas as pd

class TWStock:

    def get_data(self, stock_id, api_key):

        url = f"https://api.fugle.tw/marketdata/v1.0/stock/intraday/candles/{stock_id}"

        headers = {
            "X-API-KEY": api_key
        }

        params = {
            "timeframe": "1"
        }

        r = requests.get(url, headers=headers, params=params)
        result = r.json()

        # 防呆
        if "data" not in result:
            return pd.DataFrame({"error": [result]})

        candles = result["data"]

        df = pd.DataFrame(candles)

        # Fugle 欄位統一整理
        df = df.rename(columns={
            "close": "close",
            "open": "open",
            "high": "high",
            "low": "low",
            "volume": "volume"
        })

        return df
