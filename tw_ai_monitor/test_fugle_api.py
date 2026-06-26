import requests
import json
import re

API_KEY = "你的FUGLE_KEY"
SYMBOL = "2330"


def clean_key(key: str) -> str:
    # 1. 去掉空白/換行
    key = str(key).strip()

    # 2. 去掉所有不可見字元
    key = key.replace("\n", "").replace("\r", "").replace("\t", "")

    # 3. 只保留 ASCII（最重要）
    key = re.sub(r"[^\x20-\x7E]", "", key)

    return key


def test_api():
    api_key = clean_key(API_KEY)

    url = f"https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/{SYMBOL}"

    headers = {
        "X-API-KEY": api_key
    }

    print("KEY repr:", repr(api_key))
    print("KEY len:", len(api_key))

    try:
        res = requests.get(url, headers=headers, timeout=10)

        print("STATUS:", res.status_code)
        print("RAW:", res.text[:1000])

        try:
            data = res.json()
            print("JSON:", json.dumps(data, indent=2, ensure_ascii=False)[:2000])
        except Exception as e:
            print("JSON ERROR:", e)

    except Exception as e:
        print("REQUEST ERROR:", e)


if __name__ == "__main__":
    test_api()
