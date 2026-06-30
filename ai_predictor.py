class AIPredictor:
    @staticmethod
    def _safe_float(value, default=0.0):
        try:
            return float(value)
        except Exception:
            return default

    @staticmethod
    def _last(value, default=0.0):
        if isinstance(value, list):
            if not value:
                return default
            return AIPredictor._safe_float(value[-1], default)

        return AIPredictor._safe_float(value, default)

    @staticmethod
    def _avg(values, n=20):
        if not values:
            return 0.0

        data = [
            AIPredictor._safe_float(v)
            for v in values[-n:]
        ]

        if not data:
            return 0.0

        return sum(data) / len(data)

    @staticmethod
    def _slope(values, n=8):
        if not values or len(values) < n + 1:
            return 0.0

        start = AIPredictor._safe_float(values[-n])
        end = AIPredictor._safe_float(values[-1])

        if start == 0:
            return 0.0

        return (end - start) / start * 100

    @staticmethod
    def _recent_high(values, n=20):
        if not values:
            return 0.0

        data = [
            AIPredictor._safe_float(v)
            for v in values[-n:]
        ]

        return max(data) if data else 0.0

    @staticmethod
    def _recent_low(values, n=20):
        if not values:
            return 0.0

        data = [
            AIPredictor._safe_float(v)
            for v in values[-n:]
        ]

        return min(data) if data else 0.0

    @staticmethod
    def predict_trade(
        prices,
        volumes,
        ema5,
        ema20,
        ema60,
        rsi,
        macd,
        macd_signal,
        momentum,
        bid_ratio=1.0,
        vwap=0.0,
    ):
        prices = prices or []
        volumes = volumes or []

        price = AIPredictor._last(prices)
        prev_price = AIPredictor._safe_float(prices[-2]) if len(prices) >= 2 else price

        ema5_v = AIPredictor._last(ema5, price)
        ema20_v = AIPredictor._last(ema20, price)
        ema60_v = AIPredictor._last(ema60, price)

        rsi_v = AIPredictor._last(rsi, 50)
        macd_v = AIPredictor._last(macd, 0)
        macd_signal_v = AIPredictor._last(macd_signal, 0)
        momentum_v = AIPredictor._safe_float(momentum, 0)

        bid_ratio = AIPredictor._safe_float(bid_ratio, 1.0)
        vwap = AIPredictor._safe_float(vwap, price)

        avg_volume_20 = AIPredictor._avg(volumes, 20)
        volume_now = AIPredictor._last(volumes, 0)
        volume_ratio = volume_now / max(avg_volume_20, 1)

        price_slope = AIPredictor._slope(prices, 8)
        ema20_slope = AIPredictor._slope(ema20 if isinstance(ema20, list) else [], 8)

        recent_high = AIPredictor._recent_high(prices, 20)
        recent_low = AIPredictor._recent_low(prices, 20)

        distance_to_high = 0.0
        distance_to_low = 0.0

        if price > 0:
            distance_to_high = (recent_high - price) / price * 100
            distance_to_low = (price - recent_low) / price * 100

        vwap_gap = 0.0
        if vwap > 0:
            vwap_gap = (price - vwap) / vwap * 100

        ema_gap = 0.0
        if ema20_v > 0:
            ema_gap = (ema5_v - ema20_v) / ema20_v * 100

        macd_gap = macd_v - macd_signal_v

        reasons = []

        # =========================
        # 盤整過濾：這是提高勝率的重點
        # =========================

        too_flat = (
            abs(vwap_gap) < 0.08
            and abs(ema_gap) < 0.05
            and abs(price_slope) < 0.08
        )

        weak_volume = volume_ratio < 0.75

        if len(prices) < 35:
            return {
                "signal": "WAIT",
                "score": 35,
                "risk": "資料不足",
                "market_state": "資料累積中",
                "rebound_prob": 30,
                "reasons": ["資料不足，等待至少 35 筆資料"],
            }

        if too_flat:
            return {
                "signal": "WAIT",
                "score": 42,
                "risk": "盤整",
                "market_state": "盤整過濾",
                "rebound_prob": 45,
                "reasons": ["價格、VWAP、EMA 過度接近，盤整區不出手"],
            }

        # =========================
        # 做多評分
        # =========================

        long_score = 0
        long_reasons = []

        if price > vwap:
            long_score += 18
            long_reasons.append("價格站上 VWAP")

        if ema5_v > ema20_v:
            long_score += 16
            long_reasons.append("EMA5 站上 EMA20")

        if ema20_v >= ema60_v:
            long_score += 12
            long_reasons.append("EMA20 不弱於 EMA60")

        if macd_v > macd_signal_v:
            long_score += 14
            long_reasons.append("MACD 多方")

        if 45 <= rsi_v <= 72:
            long_score += 12
            long_reasons.append("RSI 位於可做多區間")

        if price_slope > 0:
            long_score += 8
            long_reasons.append("短線價格斜率向上")

        if ema20_slope >= 0:
            long_score += 6
            long_reasons.append("EMA20 方向不弱")

        if volume_ratio >= 1.0:
            long_score += 8
            long_reasons.append("成交量高於均量")

        if bid_ratio >= 1.08:
            long_score += 8
            long_reasons.append("五檔買盤較強")

        # 不追太高
        if distance_to_high < 0.15 and rsi_v > 68:
            long_score -= 18
            long_reasons.append("接近短線高點且 RSI 偏熱，避免追高")

        if weak_volume:
            long_score -= 10
            long_reasons.append("量能不足，降低做多分數")

        # =========================
        # 做空評分
        # =========================

        short_score = 0
        short_reasons = []

        if price < vwap:
            short_score += 18
            short_reasons.append("價格跌破 VWAP")

        if ema5_v < ema20_v:
            short_score += 16
            short_reasons.append("EMA5 跌破 EMA20")

        if ema20_v <= ema60_v:
            short_score += 12
            short_reasons.append("EMA20 不強於 EMA60")

        if macd_v < macd_signal_v:
            short_score += 14
            short_reasons.append("MACD 空方")

        if 28 <= rsi_v <= 58:
            short_score += 12
            short_reasons.append("RSI 位於可做空區間")

        if price_slope < 0:
            short_score += 8
            short_reasons.append("短線價格斜率向下")

        if ema20_slope <= 0:
            short_score += 6
            short_reasons.append("EMA20 方向不強")

        if volume_ratio >= 1.0:
            short_score += 8
            short_reasons.append("成交量高於均量")

        if bid_ratio <= 0.92:
            short_score += 8
            short_reasons.append("五檔賣壓較強")

        # 不追太低
        if distance_to_low < 0.15 and rsi_v < 32:
            short_score -= 18
            short_reasons.append("接近短線低點且 RSI 偏低，避免追空")

        if weak_volume:
            short_score -= 10
            short_reasons.append("量能不足，降低做空分數")

        # =========================
        # 嚴格出手規則
        # =========================

        long_score = max(0, min(100, long_score))
        short_score = max(0, min(100, short_score))

        if long_score >= 70 and long_score >= short_score + 12:
            signal = "BUY"
            score = long_score
            reasons = long_reasons
            market_state = "多方優勢"
            risk = "可觀察" if score < 80 else "方向明確"

        elif short_score >= 70 and short_score >= long_score + 12:
            signal = "SELL"
            score = short_score
            reasons = short_reasons
            market_state = "空方優勢"
            risk = "可觀察" if score < 80 else "方向明確"

        else:
            signal = "WAIT"
            score = max(long_score, short_score)
            reasons = [
                f"多方分數 {long_score}",
                f"空方分數 {short_score}",
                "多空差距不足，等待更明確方向",
            ]
            market_state = "等待確認"
            risk = "等待確認"

        rebound_prob = 50

        if price < vwap and rsi_v < 35 and macd_gap > 0:
            rebound_prob = 65

        elif price > vwap and rsi_v > 65 and macd_gap < 0:
            rebound_prob = 35

        return {
            "signal": signal,
            "score": int(score),
            "risk": risk,
            "market_state": market_state,
            "rebound_prob": rebound_prob,
            "reasons": reasons,
            "long_score": int(long_score),
            "short_score": int(short_score),
            "volume_ratio": round(volume_ratio, 2),
            "vwap_gap": round(vwap_gap, 3),
            "ema_gap": round(ema_gap, 3),
        }
