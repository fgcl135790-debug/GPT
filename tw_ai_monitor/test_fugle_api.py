import requests
import json

API_KEY = "YjQyNmRlNTUtMjJhNC00Y2Q5LWI0NjYtMDFhYjUzYjQ1ZWRlIGIyNzEwYTVkLTU5NTAtNDk1MC1iYzlkLWUyMGY5M2JiMmZkZQ"
SYMBOL = "2330"

def test_api():
    api_key = str(API_KEY).strip()   # 防止 hidden whitespace
    symbol = str(SYMBOL).strip()

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
