import requests
import json

API_KEY = "你的API_KEY".strip()
SYMBOL = "2330"

def test_api():

    url = f"https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/{SYMBOL}"

    headers = {
        "X-API-KEY": API_KEY.strip()   # 🔥 防止 hidden space
    }

    res = requests.get(url, headers=headers, timeout=10)

    print("\n====================")
    print("STATUS:", res.status_code)
    print("====================")

    print("\nRAW RESPONSE:")
    print(res.text[:1000])

    try:
        data = res.json()

        print("\n====================")
        print("JSON TYPE:", type(data))
        print("====================")

        print(json.dumps(data, indent=2, ensure_ascii=False)[:2000])

        # 🔥 幫你快速看結構
        if isinstance(data, dict):
            print("\nTOP KEYS:", list(data.keys()))

    except Exception as e:
        print("\nJSON PARSE ERROR:", e)


if __name__ == "__main__":
    test_api()
