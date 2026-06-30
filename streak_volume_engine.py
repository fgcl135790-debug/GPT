import math


class StreakVolumeEngine:
    """
    連次 / 連量引擎 v1

    只使用當下以前的 K 線資料，不看未來。
    目標不是看到連量就追，而是判斷：
    - 同方向攻擊是否連續
    - 同方向量能是否放大
    - 連量後價格是否真的續強 / 續弱
    - 是否出現末端爆量、吸收或追高追空風險
    """

    @staticmethod
    def _f(value, default=0.0):
        try:
            if value is None:
                return default
            if isinstance(value, float) and math.isnan(value):
                return default
            return float(value)
        except Exception:
            return default

    @staticmethod
    def _avg(values, default=0.0):
        vals = [StreakVolumeEngine._f(v) for v in (values or []) if v is not None]
        return sum(vals) / len(vals) if vals else default

    @staticmethod
    def _pct(now, prev):
        now = StreakVolumeEngine._f(now)
        prev = StreakVolumeEngine._f(prev)
        if prev <= 0:
            return 0.0
        return (now / prev - 1.0) * 100.0

    @staticmethod
    def _clamp(value, low, high):
        return max(low, min(high, value))

    @staticmethod
    def _bar_direction(open_price, close_price, prev_close=None):
        open_price = StreakVolumeEngine._f(open_price)
        close_price = StreakVolumeEngine._f(close_price)
        prev_close = StreakVolumeEngine._f(prev_close, open_price)

        # 台股 1 分 K 常有 open=close，這時用前收判斷短線推進方向。
        if close_price > open_price:
            return 1
        if close_price < open_price:
            return -1
        if close_price > prev_close:
            return 1
        if close_price < prev_close:
            return -1
        return 0

    @staticmethod
    def analyze(prices, volumes, opens=None, highs=None, lows=None, vwap_values=None):
        prices = [StreakVolumeEngine._f(x) for x in (prices or [])]
        volumes = [StreakVolumeEngine._f(x) for x in (volumes or [])]
        n = len(prices)
        if n < 8:
            return {
                "available": False,
                "buy_streak_count": 0,
                "sell_streak_count": 0,
                "buy_streak_volume": 0,
                "sell_streak_volume": 0,
                "streak_volume_ratio": 1.0,
                "streak_follow_through": 0.0,
                "volume_exhaustion_risk": 0.0,
                "absorption_risk": 0.0,
                "buy_score_adj": 0.0,
                "sell_score_adj": 0.0,
                "reasons": ["連次連量資料不足。"],
            }

        opens = [StreakVolumeEngine._f(x) for x in (opens or prices)]
        highs = [StreakVolumeEngine._f(x) for x in (highs or prices)]
        lows = [StreakVolumeEngine._f(x) for x in (lows or prices)]
        if len(opens) < n:
            opens = (opens + prices[len(opens):])[:n]
        if len(highs) < n:
            highs = (highs + prices[len(highs):])[:n]
        if len(lows) < n:
            lows = (lows + prices[len(lows):])[:n]

        dirs = []
        for i in range(n):
            prev = prices[i - 1] if i > 0 else opens[i]
            dirs.append(StreakVolumeEngine._bar_direction(opens[i], prices[i], prev))

        last_dir = dirs[-1]
        streak_count = 0
        streak_volume = 0.0
        if last_dir != 0:
            for i in range(n - 1, -1, -1):
                if dirs[i] == last_dir:
                    streak_count += 1
                    streak_volume += volumes[i] if i < len(volumes) else 0.0
                else:
                    break

        buy_streak_count = streak_count if last_dir > 0 else 0
        sell_streak_count = streak_count if last_dir < 0 else 0
        buy_streak_volume = streak_volume if last_dir > 0 else 0.0
        sell_streak_volume = streak_volume if last_dir < 0 else 0.0

        recent_window = min(max(streak_count, 3), 6)
        recent_vol = sum(volumes[-recent_window:]) if volumes else 0.0
        base_start = max(0, n - recent_window - 20)
        base_end = max(0, n - recent_window)
        base_vals = volumes[base_start:base_end]
        base_avg = StreakVolumeEngine._avg(base_vals, default=StreakVolumeEngine._avg(volumes[-20:], default=1.0))
        streak_volume_ratio = recent_vol / max(base_avg * max(recent_window, 1), 1.0)

        start_idx = max(0, n - max(streak_count, 1))
        streak_start_price = prices[start_idx]
        streak_follow_through = StreakVolumeEngine._pct(prices[-1], streak_start_price)
        if last_dir < 0:
            streak_follow_through = -streak_follow_through

        # 近期是否創短線高/低。
        lookback = min(12, n)
        recent_high_before = max(highs[-lookback:-1]) if lookback > 1 else highs[-1]
        recent_low_before = min(lows[-lookback:-1]) if lookback > 1 else lows[-1]
        breaks_short_high = prices[-1] >= recent_high_before
        breaks_short_low = prices[-1] <= recent_low_before

        # K 棒收盤位置。
        candle_range = max(highs[-1] - lows[-1], 0.000001)
        close_location = (prices[-1] - lows[-1]) / candle_range

        # 爆量但價格沒有推進 = 吸收 / 末端風險。
        volume_exhaustion_risk = 0.0
        absorption_risk = 0.0
        if streak_volume_ratio >= 1.45 and streak_follow_through < 0.18:
            absorption_risk += 10
        if streak_count >= 4 and streak_volume_ratio >= 1.60:
            if last_dir > 0 and close_location < 0.58:
                volume_exhaustion_risk += 12
            if last_dir < 0 and close_location > 0.42:
                volume_exhaustion_risk += 12
        if streak_count >= 5 and streak_follow_through < 0.25:
            absorption_risk += 8

        buy_score_adj = 0.0
        sell_score_adj = 0.0
        reasons = []
        penalties = []

        if buy_streak_count >= 2:
            buy_score_adj += min(10, buy_streak_count * 2.0)
            reasons.append(f"買方連次 {buy_streak_count} 根。")
        if sell_streak_count >= 2:
            sell_score_adj += min(10, sell_streak_count * 2.0)
            reasons.append(f"賣方連次 {sell_streak_count} 根。")

        if last_dir > 0:
            if streak_volume_ratio >= 1.25:
                buy_score_adj += min(8, (streak_volume_ratio - 1.0) * 7)
                reasons.append(f"買方連量放大 {streak_volume_ratio:.2f} 倍。")
            if breaks_short_high and streak_follow_through >= 0.18:
                buy_score_adj += 6
                reasons.append("買方連量後創短線高，具續強。")
            if volume_exhaustion_risk or absorption_risk:
                buy_score_adj -= min(14, volume_exhaustion_risk * 0.45 + absorption_risk * 0.55)
                penalties.append("買方連量但價格推進不足，疑似末端爆量或上方吸收。")
        elif last_dir < 0:
            if streak_volume_ratio >= 1.25:
                sell_score_adj += min(8, (streak_volume_ratio - 1.0) * 7)
                reasons.append(f"賣方連量放大 {streak_volume_ratio:.2f} 倍。")
            if breaks_short_low and streak_follow_through >= 0.18:
                sell_score_adj += 6
                reasons.append("賣方連量後破短線低，具續弱。")
            if volume_exhaustion_risk or absorption_risk:
                sell_score_adj -= min(14, volume_exhaustion_risk * 0.45 + absorption_risk * 0.55)
                penalties.append("賣方連量但價格推進不足，疑似恐慌末端或下方吸收。")

        # 反向連次會扣分。
        if buy_streak_count >= 2:
            sell_score_adj -= min(8, buy_streak_count * 1.6)
        if sell_streak_count >= 2:
            buy_score_adj -= min(8, sell_streak_count * 1.6)

        reasons = reasons + penalties
        if not reasons:
            reasons.append("未出現明顯連次連量。")

        return {
            "available": True,
            "last_direction": "BUY" if last_dir > 0 else ("SELL" if last_dir < 0 else "FLAT"),
            "buy_streak_count": int(buy_streak_count),
            "sell_streak_count": int(sell_streak_count),
            "buy_streak_volume": round(buy_streak_volume, 2),
            "sell_streak_volume": round(sell_streak_volume, 2),
            "streak_volume_ratio": round(streak_volume_ratio, 3),
            "streak_follow_through": round(streak_follow_through, 3),
            "breaks_short_high": bool(breaks_short_high),
            "breaks_short_low": bool(breaks_short_low),
            "close_location": round(close_location, 3),
            "volume_exhaustion_risk": round(volume_exhaustion_risk, 2),
            "absorption_risk": round(absorption_risk, 2),
            "buy_score_adj": round(buy_score_adj, 2),
            "sell_score_adj": round(sell_score_adj, 2),
            "reasons": reasons[:8],
        }
