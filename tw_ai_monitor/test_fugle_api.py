import requests
import json

# =========================
# 🔥 你只要改這一行
# =========================
API_KEY = "請貼你的Fugle API KEY"

SYMBOL = "2330"


def clean_key(key):
    if key is None:
        return ""
    return str(key).strip()


def test_api():

    api_key = clean_key(API_KEY)

    # =========================
    # 🧨 防呆：API KEY 空值直接停止
    # =========================
    if not api_key:
        print("❌ API KEY 是空的，請先填入")
        return

    url = f"https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/{SYMBOL}"

    headers = {
        "X-API-KEY": api_key
    }

    print("🔑 API KEY repr:", repr(api_key))
    print("🔑 API KEY length:", len(api_key))

    try:
        res = requests.get(url, headers=headers, timeout=10)

        print("\n====================")
        print("STATUS:", res.status_code)
        print("====================")

        print("\nRAW RESPONSE:")
        print(res.text[:800])

        try:
            data = res.json()

            print("\n====================")
            print("JSON TYPE:", type(data))
            print("====================")

            print(json.dumps(data, indent=2, ensure_ascii=False)[:2000])

            if isinstance(data, dict):
                print("\nTOP KEYS:", list(data.keys()))

        except Exception as e:
            print("❌ JSON PARSE ERROR:", e)

    except Exception as e:
        print("❌ REQUEST ERROR:", e)


if __name__ == "__main__":
    test_api()
