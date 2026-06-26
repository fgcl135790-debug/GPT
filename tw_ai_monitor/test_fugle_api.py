import requests
import json
import re

API_KEY = "你的Fugle API KEY"
SYMBOL = "2330"


def clean_key(key: str) -> str:
    """
    只保留 ASCII + 去掉換行/空白
    避免 urllib3 latin-1 encode crash
    """
    key = str(key).strip()
    key = key.replace("\n", "").replace("\r", "").replace(" ", "")
    key = re.sub(r"[^\x20-\x7E]", "", key)  # 只留可見 ASCII
    return key


def test_api():
    api_key = clean_key(API_KEY)

    url = f"https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/{SYMBOL}"

    headers = {
        "X-API-KEY": api_key
    }

    print("===== DEBUG INFO =====")
    print("API KEY repr:", repr(api_key))
    print("API KEY length:", len(api_key))
    print("URL:", url)
    print("======================")

    try:
        res = requests.get(url, headers=headers, timeout=10)

        print("STATUS:", res.status_code)
        print("RAW TEXT:", res.text[:1000])

        try:
            data = res.json()
            print("\nJSON TYPE:", type(data))

            if isinstance(data, dict):
                print("JSON KEYS:", list(data.keys()))

            print(json.dumps(data, indent=2, ensure_ascii=False)[:2000])

        except Exception as e:
            print("JSON PARSE ERROR:", e)

    except Exception as e:
        print("REQUEST ERROR:", e)


if __name__ == "__main__":
    test_api()
