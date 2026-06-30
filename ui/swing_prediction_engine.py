class SwingPredictionEngine:
    @staticmethod
    def _safe_float(value, default=0.0):
        try:
            return float(value)
        except Exception:
            return default

    @staticmethod
    def _series(value):
        if isinstance(value, list):
            return [
                SwingPredictionEngine._safe_float(v)
                for v in value
            ]

        if value is None:
            return []

        return [SwingPredictionEngine._safe_float(value)]

    @staticmethod
    def _last(value, default=0.0):
        data = SwingPredictionEngine._series(value)

        if not data:
            return default

        return data[-1]

    @staticmethod
    def _avg(values, n=20):
        data = SwingPredictionEngine._series(values)

        if not data:
            return 0.0

        data = data[-n:]

        if not data:
            return 0.0

        return sum(data) / len(data)

    @staticmethod
    def _slope_pct(values, n=10):
        data = SwingPredictionEngine._series(values)

        if len(data) < n + 1:
            return 0.0

        start = data[-n]
        end = data[-1]

        if start <= 0:
            return 0.0

        return (end - start) / start * 100

    @staticmethod
    def _recent_high(values, n=30):
        data = SwingPredictionEngine._series(values)

        if not data:
            return 0.0

        return max(data[-n:])

    @staticmethod
    def _recent_low(values, n=30):
        data = SwingPredictionEngine._series(values)

        if not data:
            return 0.0

        return min(data[-n:])

    @staticmethod
    def _clamp(value, low, high):
        return max(low, min(high, value))

    @staticmethod
    def _price_atr_pct(prices, n=14):
        data = SwingPredictionEngine._series(prices)

        if len(data) < 3:
            return 0.0

        changes = []

        for i in range(1, len(data)):
            prev = data[i - 1]
            now = data[i]

            if prev > 0:
                changes.append(abs(now - prev) / prev * 100)

        if not changes:
            return 0.0

        recent = changes[-n:]

        return sum(recent) / len(recent)

    @staticmethod
    def _macd_hist_series(macd, macd_signal):
        macd_data = SwingPredictionEngine._series(macd)
        signal_data = SwingPredictionEngine._series(macd_signal)

        n = min(len(macd_data), len(signal_data))

        if n <= 0:
            return []

        return [
            macd_data[i] - signal_data[i]
            for i in range(n)
        ]

    @staticmethod
    def analyze(
        prices,
        volumes,
        vwap,
        ema5,
        ema20,
        ema60,
        rsi,
        macd,
        macd_signal,
        bid_ratio=1.0,
        cost_pct=0.435,
    ):
        prices = SwingPredictionEngine._series(prices)
        volumes = SwingPredictionEngine._series(volumes)

        if len(prices) < 35:
            return {
                "direction": "WAIT",
                "state": "資料不足",
                "long_score": 0,
                "short_score": 0,
                "predicted_up_pct": 0,
                "predicted_down_pct": 0,
                "long_rr": 0,
                "short_rr": 0,
                "reason": "資料不足，暫不預測波段",
                "reasons": ["至少需要 35 筆以上資料"],
            }

        price = prices[-1]
        prev_price = prices[-2] if len(prices) >= 2 else price

        vwap = SwingPredictionEngine._safe_float(vwap, price)

        ema5_v = SwingPredictionEngine._last(ema5, price)
        ema20_v = SwingPredictionEngine._last(ema20, price)
        ema60_v = SwingPredictionEngine._last(ema60, price)

        rsi_data = SwingPredictionEngine._series(rsi)
        rsi_v = rsi_data[-1] if rsi_data else 50

        if len(rsi_data) >= 4:
            rsi_slope = rsi_data[-1] - rsi_data[-4]
        else:
            rsi_slope = 0.0

        macd_data = SwingPredictionEngine._series(macd)
        macd_signal_data = SwingPredictionEngine._series(macd_signal)

        macd_v = macd_data[-1] if macd_data else 0
        macd_signal_v = macd_signal_data[-1] if macd_signal_data else 0

        macd_hist_data = SwingPredictionEngine._macd_hist_series(
            macd=macd,
            macd_signal=macd_signal,
        )

        macd_hist = macd_v - macd_signal_v

        if len(macd_hist_data) >= 4:
            macd_hist_accel = macd_hist_data[-1] - macd_hist_data[-4]
        elif len(macd_hist_data) >= 2:
            macd_hist_accel = macd_hist_data[-1] - macd_hist_data[-2]
        else:
            macd_hist_accel = 0.0

        bid_ratio = SwingPredictionEngine._safe_float(bid_ratio, 1.0)
        cost_pct = SwingPredictionEngine._safe_float(cost_pct, 0.435)

        avg_volume_20 = SwingPredictionEngine._avg(volumes, 20)
        now_volume = volumes[-1] if volumes else 0
        volume_ratio = now_volume / max(avg_volume_20, 1)

        price_slope_3 = SwingPredictionEngine._slope_pct(prices, 3)
        price_slope_10 = SwingPredictionEngine._slope_pct(prices, 10)
        price_slope_20 = SwingPredictionEngine._slope_pct(prices, 20)

        ema20_slope = SwingPredictionEngine._slope_pct(
            ema20 if isinstance(ema20, list) else [],
            10,
        )

        high_30 = SwingPredictionEngine._recent_high(prices, 30)
        low_30 = SwingPredictionEngine._recent_low(prices, 30)

        high_60 = SwingPredictionEngine._recent_high(prices, 60)
        low_60 = SwingPredictionEngine._recent_low(prices, 60)

        if price > 0:
            distance_to_high_30 = (high_30 - price) / price * 100
            distance_to_low_30 = (price - low_30) / price * 100
            range_60_pct = (high_60 - low_60) / price * 100
        else:
            distance_to_high_30 = 0
            distance_to_low_30 = 0
            range_60_pct = 0

        if vwap > 0:
            vwap_gap = (price - vwap) / vwap * 100
        else:
            vwap_gap = 0.0

        if ema20_v > 0:
            ema_gap = (ema5_v - ema20_v) / ema20_v * 100
        else:
            ema_gap = 0.0

        atr_pct = SwingPredictionEngine._price_atr_pct(prices, 14)

        if atr_pct <= 0:
            atr_pct = max(range_60_pct / 12, 0.08)

        # =========================
        # 預估未來可走空間
        # 不是保證，是根據目前波動、斜率、量能、位置估算
        # =========================

        long_momentum = 0.0
        short_momentum = 0.0

        if price_slope_3 > 0:
            long_momentum += min(price_slope_3 * 0.45, 0.35)

        if price_slope_10 > 0:
            long_momentum += min(price_slope_10 * 0.35, 0.45)

        if macd_hist > 0:
            long_momentum += 0.12

        if macd_hist_accel > 0:
            long_momentum += 0.10

        if rsi_slope > 0:
            long_momentum += 0.08

        if volume_ratio >= 1.0:
            long_momentum += 0.12

        if price_slope_3 < 0:
            short_momentum += min(abs(price_slope_3) * 0.45, 0.35)

        if price_slope_10 < 0:
            short_momentum += min(abs(price_slope_10) * 0.35, 0.45)

        if macd_hist < 0:
            short_momentum += 0.12

        if macd_hist_accel < 0:
            short_momentum += 0.10

        if rsi_slope < 0:
            short_momentum += 0.08

        if volume_ratio >= 1.0:
            short_momentum += 0.12

        predicted_up_pct = (
            max(distance_to_high_30 * 0.75, atr_pct * 1.8)
            + long_momentum
        )

        predicted_down_pct = (
            max(distance_to_low_30 * 0.75, atr_pct * 1.8)
            + short_momentum
        )

        predicted_up_pct = SwingPredictionEngine._clamp(
            predicted_up_pct,
            0,
            4.5,
        )

        predicted_down_pct = SwingPredictionEngine._clamp(
            predicted_down_pct,
            0,
            4.5,
        )

        # =========================
        # 風險估算：停損不是成本，是價格反向空間
        # =========================

        long_risk_pct = max(
            0.35,
            min(1.20, atr_pct * 1.4 + max(0, abs(vwap_gap)) * 0.15),
        )

        short_risk_pct = max(
            0.35,
            min(1.20, atr_pct * 1.4 + max(0, abs(vwap_gap)) * 0.15),
        )

        long_rr = predicted_up_pct / max(long_risk_pct, 0.01)
        short_rr = predicted_down_pct / max(short_risk_pct, 0.01)

        # =========================
        # 多方預測分數
        # =========================

        long_score = 0
        long_reasons = []

        if price > vwap:
            long_score += 10
            long_reasons.append("價格在 VWAP 上方")

        if 0.02 <= vwap_gap <= 0.75:
            long_score += 14
            long_reasons.append("價格沒有離 VWAP 過遠")

        if ema5_v > ema20_v:
            long_score += 10
            long_reasons.append("EMA5 高於 EMA20")

        if ema20_v >= ema60_v:
            long_score += 7
            long_reasons.append("EMA20 不弱於 EMA60")

        if price_slope_3 > 0:
            long_score += 10
            long_reasons.append("短線 3K 轉強")

        if price_slope_10 > 0:
            long_score += 10
            long_reasons.append("10K 斜率向上")

        if macd_hist > 0:
            long_score += 8
            long_reasons.append("MACD Hist 為正")

        if macd_hist_accel > 0:
            long_score += 8
            long_reasons.append("MACD 動能正在增強")

        if 43 <= rsi_v <= 66:
            long_score += 8
            long_reasons.append("RSI 沒有過熱")

        if rsi_slope >= 0:
            long_score += 5
            long_reasons.append("RSI 正在轉強")

        if volume_ratio >= 0.8:
            long_score += 6
            long_reasons.append("量能沒有過低")

        if volume_ratio >= 1.1:
            long_score += 4
            long_reasons.append("量能放大")

        if distance_to_high_30 >= 0.35:
            long_score += 8
            long_reasons.append("距離短線高點仍有空間")

        if predicted_up_pct >= cost_pct * 1.7:
            long_score += 8
            long_reasons.append("預估上漲空間大於交易成本")

        if long_rr >= 1.25:
            long_score += 8
            long_reasons.append("多方風險報酬可接受")

        if vwap_gap > 1.0:
            long_score -= 18
            long_reasons.append("離 VWAP 太遠，避免追高")

        if distance_to_high_30 < 0.18 and rsi_v >= 62:
            long_score -= 18
            long_reasons.append("接近短線高點，避免追多")

        if rsi_v >= 72:
            long_score -= 16
            long_reasons.append("RSI 過熱")

        # =========================
        # 空方預測分數
        # =========================

        short_score = 0
        short_reasons = []

        if price < vwap:
            short_score += 10
            short_reasons.append("價格在 VWAP 下方")

        if -0.75 <= vwap_gap <= -0.02:
            short_score += 14
            short_reasons.append("價格沒有離 VWAP 過遠")

        if ema5_v < ema20_v:
            short_score += 10
            short_reasons.append("EMA5 低於 EMA20")

        if ema20_v <= ema60_v:
            short_score += 7
            short_reasons.append("EMA20 不強於 EMA60")

        if price_slope_3 < 0:
            short_score += 10
            short_reasons.append("短線 3K 轉弱")

        if price_slope_10 < 0:
            short_score += 10
            short_reasons.append("10K 斜率向下")

        if macd_hist < 0:
            short_score += 8
            short_reasons.append("MACD Hist 為負")

        if macd_hist_accel < 0:
            short_score += 8
            short_reasons.append("MACD 動能正在轉弱")

        if 34 <= rsi_v <= 58:
            short_score += 8
            short_reasons.append("RSI 沒有過低")

        if rsi_slope <= 0:
            short_score += 5
            short_reasons.append("RSI 正在轉弱")

        if volume_ratio >= 0.8:
            short_score += 6
            short_reasons.append("量能沒有過低")

        if volume_ratio >= 1.1:
            short_score += 4
            short_reasons.append("量能放大")

        if distance_to_low_30 >= 0.35:
            short_score += 8
            short_reasons.append("距離短線低點仍有空間")

        if predicted_down_pct >= cost_pct * 1.7:
            short_score += 8
            short_reasons.append("預估下跌空間大於交易成本")

        if short_rr >= 1.25:
            short_score += 8
            short_reasons.append("空方風險報酬可接受")

        if vwap_gap < -1.0:
            short_score -= 18
            short_reasons.append("離 VWAP 太遠，避免追空")

        if distance_to_low_30 < 0.18 and rsi_v <= 38:
            short_score -= 18
            short_reasons.append("接近短線低點，避免追空")

        if rsi_v <= 28:
            short_score -= 16
            short_reasons.append("RSI 過低")

        long_score = int(SwingPredictionEngine._clamp(long_score, 0, 100))
        short_score = int(SwingPredictionEngine._clamp(short_score, 0, 100))

        long_valid = (
            long_score >= 55
            and predicted_up_pct >= cost_pct * 1.2
            and long_rr >= 1.00
        )

        short_valid = (
            short_score >= 55
            and predicted_down_pct >= cost_pct * 1.2
            and short_rr >= 1.00
        )

        long_edge = long_score + predicted_up_pct * 8 + long_rr * 4
        short_edge = short_score + predicted_down_pct * 8 + short_rr * 4

        if long_valid and long_edge >= short_edge + 5:
            direction = "BUY"
            state = "多方波段起點"
            score = long_score
            reasons = long_reasons
            reason = "預估上漲空間與風險報酬較佳"

        elif short_valid and short_edge >= long_edge + 5:
            direction = "SELL"
            state = "空方波段起點"
            score = short_score
            reasons = short_reasons
            reason = "預估下跌空間與風險報酬較佳"

        else:
            direction = "WAIT"
            state = "等待更好波段"
            score = max(long_score, short_score)
            reasons = [
                f"多方分數 {long_score}",
                f"空方分數 {short_score}",
                f"預估上漲 {round(predicted_up_pct, 2)}%",
                f"預估下跌 {round(predicted_down_pct, 2)}%",
                f"多方風報 {round(long_rr, 2)}",
                f"空方風報 {round(short_rr, 2)}",
                "目前沒有足夠波段優勢",
            ]
            reason = "預估空間或風險報酬不足"

        long_target = price * (1 + predicted_up_pct / 100)
        short_target = price * (1 - predicted_down_pct / 100)

        long_stop = price * (1 - long_risk_pct / 100)
        short_stop = price * (1 + short_risk_pct / 100)

        return {
            "direction": direction,
            "state": state,
            "score": int(score),
            "reason": reason,
            "reasons": reasons,

            "price": round(price, 2),
            "prev_price": round(prev_price, 2),

            "predicted_up_pct": round(predicted_up_pct, 3),
            "predicted_down_pct": round(predicted_down_pct, 3),

            "long_score": long_score,
            "short_score": short_score,

            "long_rr": round(long_rr, 2),
            "short_rr": round(short_rr, 2),

            "long_risk_pct": round(long_risk_pct, 3),
            "short_risk_pct": round(short_risk_pct, 3),

            "long_target": round(long_target, 2),
            "short_target": round(short_target, 2),

            "long_stop": round(long_stop, 2),
            "short_stop": round(short_stop, 2),

            "vwap_gap": round(vwap_gap, 3),
            "ema_gap": round(ema_gap, 3),
            "atr_pct": round(atr_pct, 3),
            "volume_ratio": round(volume_ratio, 2),
            "price_slope_3": round(price_slope_3, 3),
            "price_slope_10": round(price_slope_10, 3),
            "price_slope_20": round(price_slope_20, 3),
            "ema20_slope": round(ema20_slope, 3),
            "rsi": round(rsi_v, 2),
            "rsi_slope": round(rsi_slope, 3),
            "macd_hist": round(macd_hist, 5),
            "macd_hist_accel": round(macd_hist_accel, 5),
            "distance_to_high_30": round(distance_to_high_30, 3),
            "distance_to_low_30": round(distance_to_low_30, 3),
            "cost_pct": round(cost_pct, 3),
        }
