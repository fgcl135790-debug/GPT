import requests
import json

def get_snapshot(api_key, symbol):

    # 🔥 強制兩種 symbol 試
    symbols = [symbol, f"{symbol}.TW"]

    for s in symbols:

        url = f"https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/{s}"

        headers = {
            "X-API-KEY": api_key
        }

        r = requests.get(url, headers=headers)

        print("\n======================")
        print("TRY SYMBOL:", s)
        print("STATUS:", r.status_code)
        print("TEXT:", r.text[:300])

        try:
            data = r.json()
            print("JSON:", json.dumps(data, indent=2, ensure_ascii=False))
        except:
            data = None

        # 如果成功就回傳
        if r.status_code == 200 and data:
            return data, None

    return None, None
