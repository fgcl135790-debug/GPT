import math


class TapeFlowEngine:
    """
    逐筆成交流近似引擎。

    目前 Fugle REST quote / 歷史 K 回測不一定有完整逐筆 tick，
    所以這裡先用「價格變化 + 成交量變化」做 tape reading proxy：
    - 上漲 K 的量視為主動買量 proxy
    - 下跌 K 的量視為主動賣量 proxy
    - 價格不動但爆量視為吸收 / 對敲風險
    - 最近 3~5 根的 delta 變化代表資金流加速度

    如果之後接到真正逐筆成交資料，只要把 tick tape 轉成相同欄位即可。
    """

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
    def analyze(prices, volumes, window=20):
        prices = [TapeFlowEngine._safe_float(x) for x in (prices or [])]
        volumes = [max(0.0, TapeFlowEngine._safe_float(x)) for x in (volumes or [])]
        n = min(len(prices), len(volumes))

        if n < 6:
            return {
                "buy_pressure": 50.0,
                "sell_pressure": 50.0,
                "net_delta_ratio": 0.0,
                "delta_acceleration": 0.0,
                "absorption_risk": 0.0,
                "large_trade_pulse": 0.0,
                "reasons": ["成交流資料不足，使用中性值。"],
            }

        prices = prices[-n:]
        volumes = volumes[-n:]
        start = max(1, n - window)

        buy_vol = 0.0
        sell_vol = 0.0
        flat_vol = 0.0
        deltas = []

        for i in range(start, n):
            p = prices[i]
            prev = prices[i - 1]
            v = volumes[i]
            if p > prev:
                buy_vol += v
                deltas.append(v)
            elif p < prev:
                sell_vol += v
                deltas.append(-v)
            else:
                flat_vol += v
                deltas.append(0.0)

        total = max(buy_vol + sell_vol + flat_vol, 1.0)
        net_delta = buy_vol - sell_vol
        net_delta_ratio = net_delta / total

        recent_delta = sum(deltas[-3:]) if deltas else 0.0
        prior_delta = sum(deltas[-10:-3]) / max(len(deltas[-10:-3]), 1) * 3 if len(deltas) > 3 else 0.0
        delta_acceleration = (recent_delta - prior_delta) / max(total, 1.0)

        recent_vol = sum(volumes[-3:]) / 3.0
        base_vol = sum(volumes[max(0, n - 23):max(0, n - 3)]) / max(len(volumes[max(0, n - 23):max(0, n - 3)]), 1)
        large_trade_pulse = recent_vol / max(base_vol, 1.0)

        price_move = abs(prices[-1] / max(prices[max(0, n - 6)], 0.000001) - 1.0) * 100.0
        vol_pulse = large_trade_pulse
        absorption_risk = 0.0
        if vol_pulse >= 1.6 and price_move < 0.18:
            absorption_risk = min(35.0, (vol_pulse - 1.5) * 18.0)

        buy_pressure = 50 + net_delta_ratio * 38 + delta_acceleration * 28
        sell_pressure = 50 - net_delta_ratio * 38 - delta_acceleration * 28

        if large_trade_pulse >= 1.4:
            if net_delta_ratio > 0:
                buy_pressure += min(10, (large_trade_pulse - 1.3) * 5)
            elif net_delta_ratio < 0:
                sell_pressure += min(10, (large_trade_pulse - 1.3) * 5)

        buy_pressure -= absorption_risk * 0.25 if net_delta_ratio > 0 else 0
        sell_pressure -= absorption_risk * 0.25 if net_delta_ratio < 0 else 0

        reasons = []
        if net_delta_ratio > 0.18:
            reasons.append("近段成交流偏主動買，買方吃單較積極。")
        elif net_delta_ratio < -0.18:
            reasons.append("近段成交流偏主動賣，賣方攻擊較積極。")
        else:
            reasons.append("近段成交流多空差距不大。")

        if large_trade_pulse >= 1.6:
            reasons.append("近 3 根量能明顯放大，疑似有大單推動。")
        if absorption_risk > 8:
            reasons.append("量放大但價格推不動，有吸收或對敲風險。")
        if delta_acceleration > 0.05:
            reasons.append("主動買量加速度轉強。")
        elif delta_acceleration < -0.05:
            reasons.append("主動賣量加速度轉強。")

        return {
            "buy_pressure": round(TapeFlowEngine._clamp(buy_pressure, 0, 100), 2),
            "sell_pressure": round(TapeFlowEngine._clamp(sell_pressure, 0, 100), 2),
            "net_delta_ratio": round(net_delta_ratio, 4),
            "delta_acceleration": round(delta_acceleration, 4),
            "absorption_risk": round(absorption_risk, 2),
            "large_trade_pulse": round(large_trade_pulse, 3),
            "buy_volume_proxy": round(buy_vol, 2),
            "sell_volume_proxy": round(sell_vol, 2),
            "reasons": reasons,
        }
