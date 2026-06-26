import requests
import pandas as pd

def get_snapshot(api_key, symbol):

    url = f"https://api.fugle.tw/marketdata/v1.0/stock/quote/{symbol}"

    headers = {
        "X-API-KEY": api_key
    }

    try:
        res = requests.get(url, headers=headers, timeout=10)

        # =========================
        # 🔥 1. 先看 HTTP 狀態碼
        # =========================
        print("STATUS:", res.status_code)

        # =========================
        # 🔥 2. 原始回應（最重要）
        # =========================
        try:
            data = res.json()
        except:
            print("RAW TEXT:", res.text)
            return None, None

        print("JSON:", data)

        # =========================
        # ❗ API KEY / QUOTA / ENDPOINT 判斷
        # =========================
        if res.status_code == 401:
            print("❌ API KEY 無效 or 未授權")
            return None, None

        if res.status_code == 404:
            print("❌ Endpoint 錯誤")
            return None, None

        if res.status_code == 429:
            print("❌ Quota 超過")
            return None, None

        # =========================
        # ❗ Fugle 格式檢查
        # =========================
        if "data" not in data:
            print("❌ 格式變更 or 無 data")
            print("完整回傳:", data)
            return None, None

        quote = data["data"].get("quote", {})

        price = (
            quote.get("tradePrice")
            or quote.get("close")
            or quote.get("price")
        )

        if price is None:
            print("❌ 沒有價格欄位")
            return None, None

        df = pd.DataFrame({
            "close": [price],
            "volume": [0]
        })

        return df, price

    except Exception as e:
        print("❌ EXCEPTION:", e)
        return None, None
