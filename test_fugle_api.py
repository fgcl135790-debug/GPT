import requests
import json

API_KEY = "你的API_KEY".strip()
SYMBOL = "2330"

def test_api():
    url = f"https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/{SYMBOL}"

    headers = {
        "X-API-KEY": API_KEY
    }

    print("API KEY repr:", repr(API_KEY))
    print("API KEY length:", len(API_KEY))

    res = requests.get(url, headers=headers)

    print("\n===== HTTP STATUS =====")
    print(res.status_code)

    print("\n===== RAW TEXT =====")
    print(res.text[:1000])

    try:
        data = res.json()

        print("\n===== JSON KEYS =====")
        print(data.keys())

        print("\n===== FULL JSON =====")
        print(json.dumps(data, indent=2, ensure_ascii=False)[:2000])

    except Exception as e:
        print("JSON ERROR:", e)


if __name__ == "__main__":
    test_api()
