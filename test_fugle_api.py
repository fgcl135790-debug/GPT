import requests
import json

API_KEY = "你的API_KEY"
SYMBOL = "2330"

def test_api():
    url = f"https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/{SYMBOL}"

    headers = {
        "X-API-KEY": API_KEY
    }

    res = requests.get(url, headers=headers)

    print("\n===== HTTP STATUS =====")
    print(res.status_code)

    print("\n===== RAW TEXT (first 1000 chars) =====")
    print(res.text[:1000])

    try:
        data = res.json()
        print("\n===== JSON STRUCTURE KEYS =====")
        print(data.keys())

        print("\n===== FULL JSON (pretty) =====")
        print(json.dumps(data, indent=2, ensure_ascii=False)[:2000])

    except Exception as e:
        print("\n❌ JSON parse error:", e)


if __name__ == "__main__":
    test_api()
