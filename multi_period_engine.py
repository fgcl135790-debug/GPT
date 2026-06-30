from datetime import datetime


class MultiPeriodEngine:

    @staticmethod
    def _safe_float(value, default=0.0):
        try:
            return float(value)
        except Exception:
            return default

    @staticmethod
    def _safe_int(value, default=0):
        try:
            return int(round(float(value)))
        except Exception:
            return default

    @staticmethod
    def _clamp(value, low=0, high=100):
        return max(low, min(high, value))

    @staticmethod
    def _to_datetime(value):
        if isinstance(value, datetime):
            return value

        try:
            return datetime.fromisoformat(str(value))
        except Exception:
            return None

    @staticmethod
    def _ema(values, span):
        nums = [MultiPeriodEngine._safe_float(v) for v in values]

        if not nums:
            return []

        alpha = 2 / (span + 1)
        result = [nums[0]]

        for v in nums[1:]:
            result.append(alpha * v + (1 - alpha) * result[-1])

        return result

    @staticmethod
    def _period_minutes(period):
        mapping = {
            "1分": 1,
            "5分": 5,
            "15分": 15,
        }

        return mapping.get(period, 1)

    @staticmethod
    def _bucket_time(dt, minutes):
        if dt is None:
            return None

        minute = (dt.minute // minutes) * minutes

        return dt.replace(
            minute=minute,
            second=0,
            microsecond=0,
        )

    @staticmethod
    def _prepare_ticks(prices, volumes, vwap_values, time_values):
        clean = []

        prices = prices or []
        volumes = volumes or []
        vwap_values = vwap_values or []
        time_values = time_values or []

        for i, price in enumerate(prices):
            p = MultiPeriodEngine._safe_float(price)

            if p <= 0:
                continue

            v = (
                MultiPeriodEngine._safe_float(volumes[i])
                if i < len(volumes)
                else 0
            )

            w = (
                MultiPeriodEngine._safe_float(vwap_values[i])
                if i < len(vwap_values)
                else p
            )

            if w <= 0:
                w = p

            t = (
                MultiPeriodEngine._to_datetime(time_values[i])
                if i < len(time_values)
                else None
            )

            clean.append(
                {
                    "price": p,
                    "volume": v,
                    "vwap": w,
                    "time": t,
                }
            )

        return clean

    @staticmethod
    def _aggregate_period(prices, volumes, vwap_values, time_values, period):
        clean = MultiPeriodEngine._prepare_ticks(
            prices=prices,
            volumes=volumes,
            vwap_values=vwap_values,
            time_values=time_values,
        )

        if not clean:
            return {
                "prices": [],
                "volumes": [],
                "vwaps": [],
            }

        if period == "1分":
            return {
                "prices": [item["price"] for item in clean],
                "volumes": [item["volume"] for item in clean],
                "vwaps": [item["vwap"] for item in clean],
            }

        minutes = MultiPeriodEngine._period_minutes(period)
        buckets = {}
        fallback_index = 0

        for item in clean:
            key = MultiPeriodEngine._bucket_time(
                item["time"],
                minutes,
            )

            if key is None:
                key = f"bucket_{fallback_index // minutes}"
                fallback_index += 1

            if key not in buckets:
                buckets[key] = {
                    "prices": [],
                    "volumes": [],
                    "vwaps": [],
                }

            buckets[key]["prices"].append(item["price"])
            buckets[key]["volumes"].append(item["volume"])
            buckets[key]["vwaps"].append(item["vwap"])

        agg_prices = []
        agg_volumes = []
        agg_vwaps = []

        for key in sorted(buckets.keys(), key=lambda x: str(x)):
            group = buckets[key]

            if not group["prices"]:
                continue

            agg_prices.append(group["prices"][-1])
            agg_volumes.append(sum(group["volumes"]))

            valid_vwaps = [
                MultiPeriodEngine._safe_float(v)
                for v in group["vwaps"]
                if MultiPeriodEngine._safe_float(v) > 0
            ]

            if valid_vwaps:
                agg_vwaps.append(sum(valid_vwaps) / len(valid_vwaps))
            else:
                agg_vwaps.append(group["prices"][-1])

        return {
            "prices": agg_prices,
            "volumes": agg_volumes,
            "vwaps": agg_vwaps,
        }

    @staticmethod
    def _analyze_one(period, prices, volumes, vwap_values, time_values):
        data = MultiPeriodEngine._aggregate_period(
            prices=prices,
            volumes=volumes,
            vwap_values=vwap_values,
            time_values=time_values,
            period=period,
        )

        ps = data["prices"]
        vs = data["volumes"]
        ws = data["vwaps"]

        if not ps:
            return {
                "period": period,
                "status": "資料不足",
                "type": "WAIT",
                "confidence": 0,
                "long_score": 0,
                "short_score": 0,
                "reason": f"{period} 資料不足",
            }

        price = ps[-1]
        prev_price = ps[-2] if len(ps) >= 2 else price

        vwap = ws[-1] if ws else price

        if vwap <= 0:
            vwap = price

        ema5_list = MultiPeriodEngine._ema(ps, 5)
        ema20_list = MultiPeriodEngine._ema(ps, 20)

        ema5 = ema5_list[-1] if ema5_list else price
        ema20 = ema20_list[-1] if ema20_list else price

        current_volume = MultiPeriodEngine._safe_float(vs[-1]) if vs else 0

        valid_volumes = [
            MultiPeriodEngine._safe_float(v)
            for v in vs[-20:]
            if MultiPeriodEngine._safe_float(v) > 0
        ]

        avg_volume = 0

        if valid_volumes:
            avg_volume = sum(valid_volumes) / len(valid_volumes)

        long_score = 0
        short_score = 0
        reasons = []

        if price > vwap:
            long_score += 2
            reasons.append("站上 VWAP")
        elif price < vwap:
            short_score += 2
            reasons.append("跌破 VWAP")

        if ema5 > ema20:
            long_score += 2
            reasons.append("EMA5 大於 EMA20")
        elif ema5 < ema20:
            short_score += 2
            reasons.append("EMA5 小於 EMA20")

        if price > prev_price:
            long_score += 1
            reasons.append("短線價格上彎")
        elif price < prev_price:
            short_score += 1
            reasons.append("短線價格下彎")

        if avg_volume > 0 and current_volume >= avg_volume * 1.35:
            if price >= prev_price:
                long_score += 1
                reasons.append("上漲伴隨量能放大")
            else:
                short_score += 1
                reasons.append("下跌伴隨量能放大")

        diff = long_score - short_score

        if diff >= 2:
            status = "多頭"
            trend_type = "BULL"
            reason = f"{period} 多方結構成立：" + "、".join(reasons[:3])

        elif diff <= -2:
            status = "空頭"
            trend_type = "BEAR"
            reason = f"{period} 空方結構成立：" + "、".join(reasons[:3])

        else:
            status = "盤整"
            trend_type = "WAIT"
            reason = f"{period} 多空條件尚未一致"

        confidence = MultiPeriodEngine._clamp(
            45 + abs(diff) * 12,
            0,
            95,
        )

        return {
            "period": period,
            "status": status,
            "type": trend_type,
            "confidence": confidence,
            "long_score": long_score,
            "short_score": short_score,
            "price": price,
            "vwap": vwap,
            "ema5": ema5,
            "ema20": ema20,
            "reason": reason,
        }

    @staticmethod
    def analyze(prices, volumes, vwap_values, time_values):
        periods = ["1分", "5分", "15分"]

        results = [
            MultiPeriodEngine._analyze_one(
                period=period,
                prices=prices,
                volumes=volumes,
                vwap_values=vwap_values,
                time_values=time_values,
            )
            for period in periods
        ]

        bull_count = len([r for r in results if r["type"] == "BULL"])
        bear_count = len([r for r in results if r["type"] == "BEAR"])
        wait_count = len([r for r in results if r["type"] == "WAIT"])

        avg_confidence = MultiPeriodEngine._safe_int(
            sum([r["confidence"] for r in results]) / max(len(results), 1)
        )

        if bull_count == 3:
            resonance = "BULL_STRONG"
            status = "多頭共振"
            score_delta = 10
            long_boost = 5
            short_boost = 0
            reason = "1分、5分、15分同步多頭共振，提升做多信心"

        elif bear_count == 3:
            resonance = "BEAR_STRONG"
            status = "空頭共振"
            score_delta = 10
            long_boost = 0
            short_boost = 5
            reason = "1分、5分、15分同步空頭共振，提升做空信心"

        elif bull_count >= 2 and bear_count == 0:
            resonance = "BULL"
            status = "多方偏強"
            score_delta = 6
            long_boost = 3
            short_boost = 0
            reason = "多數週期偏多，多方結構較完整"

        elif bear_count >= 2 and bull_count == 0:
            resonance = "BEAR"
            status = "空方偏強"
            score_delta = 6
            long_boost = 0
            short_boost = 3
            reason = "多數週期偏空，空方壓力較明顯"

        elif bull_count >= 1 and bear_count >= 1:
            resonance = "DIVERGENCE"
            status = "多空背離"
            score_delta = -8
            long_boost = 0
            short_boost = 0
            reason = "多週期方向不一致，容易震盪或假突破"

        else:
            resonance = "WAIT"
            status = "盤整觀望"
            score_delta = -3
            long_boost = 0
            short_boost = 0
            reason = "三週期尚未形成共振，等待方向確認"

        return {
            "resonance": resonance,
            "status": status,
            "score_delta": score_delta,
            "long_boost": long_boost,
            "short_boost": short_boost,
            "confidence": avg_confidence,
            "bull_count": bull_count,
            "bear_count": bear_count,
            "wait_count": wait_count,
            "reason": reason,
            "results": results,
        }

    @staticmethod
    def apply_to_decision(decision, multi_period):
        decision = dict(decision or {})
        multi_period = multi_period or {}

        action = decision.get("action", "WAIT")

        score = MultiPeriodEngine._safe_int(
            decision.get("score", 50),
            50,
        )

        long_score = MultiPeriodEngine._safe_int(
            decision.get("long_score", 0),
            0,
        )

        short_score = MultiPeriodEngine._safe_int(
            decision.get("short_score", 0),
            0,
        )

        reasons = list(decision.get("reasons", []))

        resonance = multi_period.get("resonance", "WAIT")
        status = multi_period.get("status", "盤整觀望")
        reason = multi_period.get("reason", "多週期尚未形成明確共振")

        score_delta = MultiPeriodEngine._safe_int(
            multi_period.get("score_delta", 0),
            0,
        )

        long_boost = MultiPeriodEngine._safe_int(
            multi_period.get("long_boost", 0),
            0,
        )

        short_boost = MultiPeriodEngine._safe_int(
            multi_period.get("short_boost", 0),
            0,
        )

        long_score += long_boost
        short_score += short_boost

        # 多週期共振會提高信心；背離會降低信心
        score += score_delta

        # 如果交易方向與多週期強共振相反，先降成觀望
        if action == "BUY" and resonance in ["BEAR_STRONG", "BEAR"]:
            action = "WAIT"
            score -= 10
            reasons.insert(
                0,
                "交易方向與多週期空方結構衝突，暫不追多",
            )

        elif action == "SELL" and resonance in ["BULL_STRONG", "BULL"]:
            action = "WAIT"
            score -= 10
            reasons.insert(
                0,
                "交易方向與多週期多方結構衝突，暫不追空",
            )

        else:
            reasons.insert(
                0,
                reason,
            )

        # 原本是觀望時，允許多週期共振補強方向，但不過度激進
        bias = long_score - short_score

        if action == "WAIT":
            if bias >= 6 and score >= 68:
                action = "BUY"
                reasons.insert(
                    0,
                    "多週期共振補強，多方條件達到短線觀察門檻",
                )

            elif bias <= -6 and score >= 68:
                action = "SELL"
                reasons.insert(
                    0,
                    "多週期共振補強，空方條件達到短線觀察門檻",
                )

        score = MultiPeriodEngine._clamp(score, 0, 100)

        decision["action"] = action
        decision["score"] = score
        decision["long_score"] = long_score
        decision["short_score"] = short_score
        decision["bias"] = bias
        decision["reasons"] = reasons[:8]
        decision["multi_period"] = multi_period
        decision["multi_period_status"] = status

        return decision
