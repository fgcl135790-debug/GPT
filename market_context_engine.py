import math


class MarketContextEngine:
    """盤勢分類引擎：趨勢 / 震盪 / 急拉急殺 / 量縮盤。"""

    @staticmethod
    def _safe_float(value, default=0.0):
        try:
            if value is None:
                return default
            if isinstance(value, float) and math.isnan(value):
                return default
            return float(value)
        except Exception:
            return default

    @staticmethod
    def _pct(a, b):
        a = MarketContextEngine._safe_float(a)
        b = MarketContextEngine._safe_float(b)
        if b <= 0:
            return 0.0
        return (a / b - 1) * 100

    @staticmethod
    def _avg(values, default=0.0):
        vals = [MarketContextEngine._safe_float(x) for x in (values or []) if x is not None]
        if not vals:
            return default
        return sum(vals) / len(vals)

    @staticmethod
    def _clamp(value, low, high):
        return max(low, min(high, value))

    @staticmethod
    def analyze(prices, volumes, highs=None, lows=None, vwap_values=None):
        prices = [MarketContextEngine._safe_float(x) for x in (prices or [])]
        volumes = [max(0.0, MarketContextEngine._safe_float(x)) for x in (volumes or [])]
        n = min(len(prices), len(volumes))
        if n < 20:
            return {
                "regime": "DATA_SHORT",
                "trend": "WAIT",
                "quality": 45.0,
                "volatility_pct": 0.0,
                "range_pct": 0.0,
                "reasons": ["盤勢資料不足。"],
            }

        prices = prices[-n:]
        highs = [MarketContextEngine._safe_float(x) for x in (highs or prices)]
        lows = [MarketContextEngine._safe_float(x) for x in (lows or prices)]
        if len(highs) < n:
            highs = (highs + prices[len(highs):])[:n]
        if len(lows) < n:
            lows = (lows + prices[len(lows):])[:n]

        price = prices[-1]
        day_high = max(highs)
        day_low = min(lows)
        range_pct = (day_high - day_low) / max(price, 0.000001) * 100
        slope_10 = MarketContextEngine._pct(price, prices[-11]) if n >= 11 else 0
        slope_20 = MarketContextEngine._pct(price, prices[-21]) if n >= 21 else 0
        slope_40 = MarketContextEngine._pct(price, prices[-41]) if n >= 41 else slope_20

        if vwap_values and len(vwap_values) >= n:
            vwap = MarketContextEngine._safe_float(vwap_values[-1], price)
        else:
            amount = sum(p * v for p, v in zip(prices, volumes))
            volsum = sum(volumes)
            vwap = amount / volsum if volsum > 0 else price
        vwap_gap = MarketContextEngine._pct(price, vwap)

        # 波動 proxy：最近 20 根平均實體變化
        changes = [abs(MarketContextEngine._pct(prices[i], prices[i - 1])) for i in range(max(1, n - 20), n)]
        volatility_pct = MarketContextEngine._avg(changes)
        vol_now = MarketContextEngine._avg(volumes[-5:], 0)
        vol_base = MarketContextEngine._avg(volumes[-25:-5], max(vol_now, 1))
        volume_regime = vol_now / max(vol_base, 1)

        reasons = []
        trend = "WAIT"
        regime = "RANGE"
        quality = 50.0

        if range_pct < 0.9 and volatility_pct < 0.09:
            regime = "LOW_VOL_RANGE"
            quality -= 12
            reasons.append("當日波動偏小，停利空間不足。")
        elif slope_20 > 0.55 and vwap_gap > 0.1:
            regime = "TREND_UP"
            trend = "BUY"
            quality += 12
            reasons.append("盤勢偏多方趨勢，順勢做多品質提高。")
        elif slope_20 < -0.55 and vwap_gap < -0.1:
            regime = "TREND_DOWN"
            trend = "SELL"
            quality += 12
            reasons.append("盤勢偏空方趨勢，順勢做空品質提高。")
        elif abs(slope_20) < 0.25 and abs(vwap_gap) < 0.35:
            regime = "VWAP_CHOP"
            quality -= 6
            reasons.append("價格貼近 VWAP 震盪，假訊號機率較高。")
        else:
            regime = "MIXED"
            reasons.append("盤勢混合，需等待量價方向確認。")

        if volume_regime >= 1.35:
            quality += 6
            reasons.append("近 5 根量能高於基準，盤中推動力提高。")
        elif volume_regime <= 0.65:
            quality -= 6
            reasons.append("近 5 根量能偏低，訊號延續性較弱。")

        if slope_10 > 0.45 and slope_20 > 0.2:
            trend = "BUY"
        elif slope_10 < -0.45 and slope_20 < -0.2:
            trend = "SELL"

        return {
            "regime": regime,
            "trend": trend,
            "quality": round(MarketContextEngine._clamp(quality, 0, 100), 2),
            "range_pct": round(range_pct, 3),
            "volatility_pct": round(volatility_pct, 4),
            "volume_regime": round(volume_regime, 3),
            "slope_10": round(slope_10, 3),
            "slope_20": round(slope_20, 3),
            "slope_40": round(slope_40, 3),
            "vwap_gap": round(vwap_gap, 3),
            "reasons": reasons,
        }
