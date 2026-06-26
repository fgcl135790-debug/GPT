import requests
import json

API_KEY = "你的API_KEY"

def clean_key(key):
    return str(key).strip().encode("utf-8").decode("utf-8")

def test_api():

    api_key = clean_key(API_KEY)
    symbol = "2330"

    url = f"https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/{symbol}"

    headers = {
        "X-API-KEY": api_key
    }

    print("API KEY repr:", repr(api_key))
    print("API KEY length:", len(api_key))

    try:
        res = requests.get(url, headers=headers, timeout=10)

        print("\nSTATUS:", res.status_code)
        print("\nRAW:", res.text[:500])

        try:
            data = res.json()
            print("\nJSON KEYS:", list(data.keys()) if isinstance(data, dict) else type(data))
            print(json.dumps(data, indent=2, ensure_ascii=False)[:2000])
        except Exception as e:
            print("JSON ERROR:", e)

    except Exception as e:
        print("REQUEST ERROR:", e)


if __name__ == "__main__":
    test_api()
