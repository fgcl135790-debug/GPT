import math


class AdaptiveRiskEngine:
    """根據當日波動 / ORB 寬度 / 量能，動態建議停損停利。"""

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
    def _clamp(value, low, high):
        return max(low, min(high, value))

    @staticmethod
    def suggest(
        prices,
        highs=None,
        lows=None,
        volumes=None,
        base_stop_pct=0.7,
        base_take_pct=1.8,
        cost_pct=0.435,
    ):
        prices = [AdaptiveRiskEngine._safe_float(x) for x in (prices or [])]
        n = len(prices)
        if n < 20:
            return {
                "stop_pct": base_stop_pct,
                "take_pct": base_take_pct,
                "risk_reward": round(base_take_pct / max(base_stop_pct, 0.01), 2),
                "mode": "base",
                "reasons": ["資料不足，使用固定停損停利。"],
            }

        highs = [AdaptiveRiskEngine._safe_float(x) for x in (highs or prices)]
        lows = [AdaptiveRiskEngine._safe_float(x) for x in (lows or prices)]
        volumes = [max(0.0, AdaptiveRiskEngine._safe_float(x)) for x in (volumes or [])]
        if len(highs) < n:
            highs = (highs + prices[len(highs):])[:n]
        if len(lows) < n:
            lows = (lows + prices[len(lows):])[:n]

        price = prices[-1]
        ranges = []
        for h, l, p in zip(highs[-20:], lows[-20:], prices[-20:]):
            ranges.append((h - l) / max(p, 0.000001) * 100)
        atr20_pct = sum(ranges) / max(len(ranges), 1)

        orb_len = min(15, n)
        orb_width_pct = (max(highs[:orb_len]) - min(lows[:orb_len])) / max(price, 0.000001) * 100
        day_range_pct = (max(highs) - min(lows)) / max(price, 0.000001) * 100

        recent_vol = sum(volumes[-5:]) / 5 if len(volumes) >= 5 else 0
        base_vols = volumes[-30:-5] if len(volumes) >= 30 else volumes[:-5]
        base_vol = sum(base_vols) / max(len(base_vols), 1) if base_vols else max(recent_vol, 1)
        vol_ratio = recent_vol / max(base_vol, 1)

        # 停損以近期雜訊為基準，停利以日內可達波動 + ORB 寬度估計。
        adaptive_stop = max(base_stop_pct * 0.85, atr20_pct * 3.2, orb_width_pct * 0.38)
        adaptive_take = max(base_take_pct * 0.75, adaptive_stop * 1.8, min(day_range_pct * 0.75, base_take_pct * 1.25))

        # 低波動日停利縮小，避免目標不切實際；高量趨勢日放大一點。
        if day_range_pct < 1.4:
            adaptive_take = min(adaptive_take, max(1.0, day_range_pct * 0.85))
        if vol_ratio >= 1.45 and day_range_pct >= 1.5:
            adaptive_take *= 1.08
        if vol_ratio <= 0.65:
            adaptive_take *= 0.9

        # 當沖監控以固定參數為核心，動態風控只做小幅調整，
        # 避免模型因為停損放太寬而把風險放大。
        adaptive_stop = AdaptiveRiskEngine._clamp(adaptive_stop, max(0.45, base_stop_pct * 0.8), min(0.9, base_stop_pct * 1.25))
        adaptive_take = AdaptiveRiskEngine._clamp(adaptive_take, max(1.1, base_take_pct * 0.75), min(2.1, base_take_pct * 1.15))

        # 保持基本損益比；如果停利被低波動壓太近，停損也要縮。
        if adaptive_take / max(adaptive_stop, 0.01) < 1.45:
            adaptive_stop = min(adaptive_stop, adaptive_take / 1.45)
            adaptive_stop = AdaptiveRiskEngine._clamp(adaptive_stop, max(0.45, base_stop_pct * 0.8), min(0.9, base_stop_pct * 1.25))

        required = (adaptive_stop + cost_pct) / max((adaptive_take - cost_pct) + (adaptive_stop + cost_pct), 0.000001) * 100

        reasons = [
            f"ATR20 約 {atr20_pct:.2f}%，ORB 寬 {orb_width_pct:.2f}%，日內區間 {day_range_pct:.2f}%",
            f"量能倍率 {vol_ratio:.2f}，動態停損 {adaptive_stop:.2f}%，停利 {adaptive_take:.2f}%",
        ]

        return {
            "stop_pct": round(adaptive_stop, 3),
            "take_pct": round(adaptive_take, 3),
            "risk_reward": round(adaptive_take / max(adaptive_stop, 0.01), 2),
            "required_win_rate": round(required, 2),
            "atr20_pct": round(atr20_pct, 3),
            "orb_width_pct": round(orb_width_pct, 3),
            "day_range_pct": round(day_range_pct, 3),
            "volume_ratio": round(vol_ratio, 3),
            "mode": "adaptive",
            "reasons": reasons,
        }
