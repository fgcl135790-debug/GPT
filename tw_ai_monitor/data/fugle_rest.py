import requests
import json

def get_snapshot(api_key, symbol):

    url = f"https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/{symbol}"

    headers = {
        "X-API-KEY": api_key
    }

    r = requests.get(url, headers=headers)

    print("\n===== API DEBUG START =====")
    print("STATUS:", r.status_code)
    print("TEXT:", r.text)

    try:
        data = r.json()
        print("JSON:\n", json.dumps(data, indent=2, ensure_ascii=False))
    except Exception as e:
        print("JSON PARSE ERROR:", e)
        data = None

    print("===== API DEBUG END =====\n")

    # ❗先不要做任何解析
    return None, None
