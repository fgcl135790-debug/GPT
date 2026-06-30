import requests


class FugleProvider:
    """
    Fugle REST Provider 修正版。

    不再依賴 fugle_marketdata 套件，直接使用官方 REST endpoint：
    https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/{symbol}

    這樣可以避免 Streamlit Cloud 套件版本或 WebSocket 權限造成主畫面卡住。
    """

    BASE_URL = "https://api.fugle.tw/marketdata/v1.0/stock"

    def __init__(self, api_key):
        self.api_key = self._clean_api_key(api_key)

    @staticmethod
    def _clean_api_key(api_key):
        return str(api_key or "").strip().replace("\n", "").replace("\r", "")

    @staticmethod
    def _safe_float(value, default=0.0):
        try:
            if value is None:
                return default
            return float(value)
        except Exception:
            return default

    @staticmethod
    def _safe_int(value, default=0):
        try:
            if value is None:
                return default
            return int(round(float(value)))
        except Exception:
            return default

    @staticmethod
    def _normalize_levels(levels):
        if not isinstance(levels, list):
            return []

        result = []

        for item in levels[:5]:
            if not isinstance(item, dict):
                continue

            result.append(
                {
                    "price": FugleProvider._safe_float(item.get("price"), 0),
                    "size": FugleProvider._safe_float(item.get("size"), 0),
                }
            )

        while len(result) < 5:
            result.append({"price": 0, "size": 0})

        return result

    def get_quote(self, symbol):
        if not self.api_key:
            raise RuntimeError("missing Fugle API key")

        symbol = str(symbol or "").strip()

        if not symbol:
            raise RuntimeError("missing stock symbol")

        url = f"{self.BASE_URL}/intraday/quote/{symbol}"

        headers = {
            "X-API-KEY": self.api_key,
        }

        response = requests.get(
            url,
            headers=headers,
            timeout=20,
        )

        if response.status_code == 401:
            raise RuntimeError("Fugle API KEY 無效或權限不足。")

        if response.status_code == 403:
            raise RuntimeError("Fugle API 權限不足，請確認方案與 endpoint 權限。")

        if response.status_code == 429:
            raise RuntimeError("Fugle API 請求過多，請稍後再試。")

        if response.status_code >= 400:
            raise RuntimeError(f"Fugle API 錯誤：HTTP {response.status_code}")

        data = response.json()

        if not isinstance(data, dict):
            raise RuntimeError("Fugle 回傳格式不是 JSON object。")

        price = (
            self._safe_float(data.get("lastPrice"), 0)
            or self._safe_float(data.get("closePrice"), 0)
            or self._safe_float(data.get("close"), 0)
        )

        open_price = (
            self._safe_float(data.get("openPrice"), 0)
            or self._safe_float(data.get("open"), 0)
            or price
        )

        high_price = (
            self._safe_float(data.get("highPrice"), 0)
            or self._safe_float(data.get("high"), 0)
            or price
        )

        low_price = (
            self._safe_float(data.get("lowPrice"), 0)
            or self._safe_float(data.get("low"), 0)
            or price
        )

        vwap = (
            self._safe_float(data.get("avgPrice"), 0)
            or self._safe_float(data.get("vwap"), 0)
            or price
        )

        return {
            "name": data.get("name") or symbol,
            "price": price,
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "vwap": vwap,
            "last_size": self._safe_float(data.get("lastSize"), 0),
            "bids": self._normalize_levels(data.get("bids", [])),
            "asks": self._normalize_levels(data.get("asks", [])),
            "trade": data.get("lastTrade", {}) or {},
            "is_close": bool(data.get("isClose", False)),
            "raw": data,
        }
