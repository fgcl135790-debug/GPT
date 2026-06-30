import math


class SignalQualityEngine:
    """
    Signal Quality Engine v1

    目標：不是增加出手次數，而是判斷這筆 BUY / SELL 是否「扣成本後值得做」。
    只使用當下以前已知資料，不使用未來 K 線，不做事後挑點。

    輸出重點：
    - estimated_mfe_pct：預估最大有利波動
    - estimated_mae_pct：預估最大不利波動
    - mfe_mae_ratio：預估有利 / 不利比
    - ev_after_quality：把 MFE/MAE 品質折扣後的期望值
    - pass_quality_gate：是否通過交易品質閘門
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
    def _clamp(value, low, high):
        return max(low, min(high, value))

    @staticmethod
    def _avg(values, default=0.0):
        vals = [SignalQualityEngine._f(v) for v in (values or []) if v is not None]
        return sum(vals) / len(vals) if vals else default

    @staticmethod
    def _range_pct(high, low, ref):
        high = SignalQualityEngine._f(high)
        low = SignalQualityEngine._f(low)
        ref = max(SignalQualityEngine._f(ref), 0.000001)
        return max(0.0, (high - low) / ref * 100.0)

    @staticmethod
    def evaluate(
        action,
        chosen,
        feature,
        tape_flow=None,
        orderbook_flow=None,
        market_context=None,
        risk_plan=None,
        rest_microstructure=None,
        streak_volume=None,
        stop_pct=0.7,
        take_pct=1.8,
        cost_pct=0.435,
        min_quality_ev=0.06,
        min_mfe_mae_ratio=1.15,
    ):
        action = str(action or "WAIT").upper()
        chosen = chosen or {}
        feature = feature or {}
        tape_flow = tape_flow or {}
        orderbook_flow = orderbook_flow or {}
        market_context = market_context or {}
        risk_plan = risk_plan or {}
        rest_microstructure = rest_microstructure or {}
        streak_volume = streak_volume or {}

        if action not in ["BUY", "SELL"]:
            return {
                "pass_quality_gate": False,
                "quality_score": 0,
                "quality_adjustment": -99,
                "estimated_mfe_pct": 0,
                "estimated_mae_pct": 0,
                "mfe_mae_ratio": 0,
                "ev_after_quality": 0,
                "quality_reasons": ["沒有 BUY / SELL 候選，不評估品質。"],
                "quality_fail_reasons": ["無方向候選"],
            }

        stop_pct = SignalQualityEngine._f(risk_plan.get("stop_pct", stop_pct), stop_pct)
        take_pct = SignalQualityEngine._f(risk_plan.get("take_pct", take_pct), take_pct)
        cost_pct = SignalQualityEngine._f(cost_pct, 0.435)
        predicted_ev = SignalQualityEngine._f(chosen.get("expected_value"), 0.0)
        base_score = SignalQualityEngine._f(chosen.get("score"), 0.0)
        price = max(SignalQualityEngine._f(feature.get("price"), 0.0), 0.000001)

        day_high = SignalQualityEngine._f(feature.get("day_high"), price)
        day_low = SignalQualityEngine._f(feature.get("day_low"), price)
        vwap_gap = SignalQualityEngine._f(feature.get("vwap_gap"), 0.0)
        slope_3 = SignalQualityEngine._f(feature.get("slope_3"), 0.0)
        slope_5 = SignalQualityEngine._f(feature.get("slope_5"), 0.0)
        slope_10 = SignalQualityEngine._f(feature.get("slope_10"), 0.0)
        volume_ratio_5 = SignalQualityEngine._f(feature.get("volume_ratio_5"), 1.0)
        volume_accel = SignalQualityEngine._f(feature.get("volume_acceleration"), 1.0)
        close_loc = SignalQualityEngine._f(feature.get("close_location"), 0.5)
        minute = SignalQualityEngine._f(feature.get("clock_minute", feature.get("minute_index", 0)), 0.0)
        day_range_pct = SignalQualityEngine._f(feature.get("day_range_pct"), 0.0)

        tape_buy = SignalQualityEngine._f(tape_flow.get("buy_pressure"), 50.0)
        tape_sell = SignalQualityEngine._f(tape_flow.get("sell_pressure"), 50.0)
        ob_buy = SignalQualityEngine._f(orderbook_flow.get("buy_pressure"), 50.0)
        ob_sell = SignalQualityEngine._f(orderbook_flow.get("sell_pressure"), 50.0)
        market_quality = SignalQualityEngine._f(market_context.get("quality"), 50.0)
        trend = str(market_context.get("trend", market_context.get("direction", "")) or "")
        execution_risk = str(rest_microstructure.get("execution_risk", "") or "")
        slippage_add = SignalQualityEngine._f(rest_microstructure.get("effective_cost_add_pct"), 0.0)
        streak_available = bool(streak_volume.get("available", False))
        buy_streak_count = SignalQualityEngine._f(streak_volume.get("buy_streak_count"), 0.0)
        sell_streak_count = SignalQualityEngine._f(streak_volume.get("sell_streak_count"), 0.0)
        streak_volume_ratio = SignalQualityEngine._f(streak_volume.get("streak_volume_ratio"), 1.0)
        streak_follow = SignalQualityEngine._f(streak_volume.get("streak_follow_through"), 0.0)
        streak_exhaustion = SignalQualityEngine._f(streak_volume.get("volume_exhaustion_risk"), 0.0)
        streak_absorption = SignalQualityEngine._f(streak_volume.get("absorption_risk"), 0.0)

        # 已知「空間」：做多看上方空間，做空看下方空間。
        upside_room_pct = max(0.0, (day_high - price) / price * 100.0)
        downside_room_pct = max(0.0, (price - day_low) / price * 100.0)

        # 盤中波動 proxy：不用未來，只用目前已知 day range 與動能估計。
        volatility_budget = SignalQualityEngine._clamp(day_range_pct * 0.42 + abs(slope_10) * 0.55, 0.18, 3.2)
        volume_boost = SignalQualityEngine._clamp((volume_ratio_5 - 1.0) * 0.16 + (volume_accel - 1.0) * 0.12, -0.22, 0.45)
        context_boost = SignalQualityEngine._clamp((market_quality - 50.0) * 0.012, -0.25, 0.35)
        slippage_penalty = SignalQualityEngine._clamp(slippage_add * 0.9, 0.0, 0.45)

        reasons = []
        fails = []
        adjustment = 0.0

        if action == "BUY":
            direction_momentum = slope_3 * 0.35 + slope_5 * 0.35 + slope_10 * 0.30
            tape_edge = (tape_buy - tape_sell) / 100.0
            ob_edge = (ob_buy - ob_sell) / 100.0
            close_bonus = (close_loc - 0.5) * 0.55
            room_pct = max(upside_room_pct, take_pct * 0.50)
            adverse_room_pct = downside_room_pct

            if close_loc < 0.48:
                adjustment -= 8
                fails.append("BUY K棒收盤位置偏弱")
            if vwap_gap > 1.8:
                adjustment -= 8
                fails.append("BUY 離 VWAP 偏遠，追高風險")
            if upside_room_pct < take_pct * 0.35 and minute > 20:
                adjustment -= 6
                fails.append("上方已知空間偏小")
            if tape_buy > tape_sell + 8:
                reasons.append("Tape 主動買壓優於賣壓")
            if ob_buy > ob_sell + 8:
                reasons.append("五檔買盤支撐優於賣壓")
            if streak_available:
                if buy_streak_count >= 3 and streak_volume_ratio >= 1.15 and streak_follow >= 0.15:
                    adjustment += 6
                    reasons.append("買方連次連量且價格續強")
                elif sell_streak_count >= 2:
                    adjustment -= 5
                    fails.append("反向賣方連次明顯")
                if streak_exhaustion >= 8 or streak_absorption >= 8:
                    adjustment -= 6
                    fails.append("連量後推進不足，疑似末端爆量或吸收")

        else:
            direction_momentum = -(slope_3 * 0.35 + slope_5 * 0.35 + slope_10 * 0.30)
            tape_edge = (tape_sell - tape_buy) / 100.0
            ob_edge = (ob_sell - ob_buy) / 100.0
            close_bonus = (0.5 - close_loc) * 0.55
            room_pct = max(downside_room_pct, take_pct * 0.50)
            adverse_room_pct = upside_room_pct

            if close_loc > 0.52:
                adjustment -= 8
                fails.append("SELL K棒收盤位置偏強")
            if vwap_gap < -1.8:
                adjustment -= 8
                fails.append("SELL 離 VWAP 偏遠，追空風險")
            if downside_room_pct < take_pct * 0.35 and minute > 20:
                adjustment -= 6
                fails.append("下方已知空間偏小")
            if tape_sell > tape_buy + 8:
                reasons.append("Tape 主動賣壓優於買壓")
            if ob_sell > ob_buy + 8:
                reasons.append("五檔賣壓優於買盤")
            if streak_available:
                if sell_streak_count >= 3 and streak_volume_ratio >= 1.15 and streak_follow >= 0.15:
                    adjustment += 6
                    reasons.append("賣方連次連量且價格續弱")
                elif buy_streak_count >= 2:
                    adjustment -= 5
                    fails.append("反向買方連次明顯")
                if streak_exhaustion >= 8 or streak_absorption >= 8:
                    adjustment -= 6
                    fails.append("連量後推進不足，疑似恐慌末端或吸收")

        # 時段品質：不是硬封鎖，只做合理加減分.
        if 15 <= minute <= 35:
            adjustment += 4
            reasons.append("早盤主波段時段，允許較積極判斷")
        elif 90 <= minute <= 125:
            adjustment -= 5
            reasons.append("10:30 後容易出現二次攻擊假訊號，門檻加嚴")
        elif minute >= 180:
            adjustment -= 8
            fails.append("午盤後低量與滑價風險提高")

        if volume_ratio_5 >= 1.5 and volume_accel >= 1.05:
            adjustment += 5
            reasons.append("量能放大且有加速度")
        elif volume_ratio_5 < 0.75:
            adjustment -= 5
            fails.append("量能不足，停利推動力偏弱")

        if direction_momentum > 0.18:
            adjustment += 5
            reasons.append("短線斜率與方向同向")
        elif direction_momentum < -0.05:
            adjustment -= 7
            fails.append("短線斜率與進場方向不一致")

        if tape_edge > 0.08:
            adjustment += 4
        elif tape_edge < -0.08:
            adjustment -= 5
            fails.append("成交流與進場方向相反")

        if ob_edge > 0.08:
            adjustment += 3
        elif ob_edge < -0.10:
            adjustment -= 4
            fails.append("五檔壓力與進場方向相反")

        if "HIGH" in execution_risk.upper() or "高" in execution_risk:
            adjustment -= 6
            fails.append("成交難度或滑價風險偏高")

        # 預估 MFE / MAE：保守估，不偷看未來。
        mfe = (
            volatility_budget * 0.55
            + max(direction_momentum, -0.1) * 0.65
            + max(tape_edge, -0.1) * 0.45
            + max(ob_edge, -0.1) * 0.25
            + volume_boost
            + context_boost
            + close_bonus
        )
        mfe = min(max(0.05, mfe), max(room_pct + 0.55, take_pct * 1.25))

        mae = (
            stop_pct * 0.58
            + max(-direction_momentum, 0) * 0.38
            + max(-tape_edge, 0) * 0.26
            + max(-ob_edge, 0) * 0.20
            + max(0, slippage_penalty)
        )
        if volume_ratio_5 < 0.8:
            mae += 0.10
        if adverse_room_pct < stop_pct * 0.35 and minute > 20:
            # 附近有已知支撐/壓力，不一定壞，降低不利波動估計。
            mae -= 0.08
        mae = SignalQualityEngine._clamp(mae, 0.08, max(stop_pct * 1.65, 0.25))

        ratio = mfe / max(mae, 0.000001)
        quality_score = SignalQualityEngine._clamp(base_score + adjustment + (ratio - 1.0) * 7.5, 0, 100)

        # 品質後 EV：方向原始 EV + MFE/MAE結構優勢 - 滑價/品質風險。
        ev_after_quality = predicted_ev + (mfe - mae) * 0.28 + adjustment * 0.006 - slippage_penalty * 0.55
        ev_after_quality = round(ev_after_quality, 3)

        if mfe < take_pct * 0.42:
            fails.append("預估有利波動不足以支撐停利")
        if ratio < min_mfe_mae_ratio:
            fails.append("預估 MFE/MAE 比不足")
        if ev_after_quality < min_quality_ev:
            fails.append("品質調整後扣成本期望不足")

        hard_fail_count = len(fails)
        pass_gate = (
            ev_after_quality >= min_quality_ev
            and ratio >= min_mfe_mae_ratio
            and mfe >= take_pct * 0.36
            and hard_fail_count <= 2
        )

        if not reasons:
            reasons.append("訊號品質中性，未看到明顯額外加分。")

        return {
            "pass_quality_gate": bool(pass_gate),
            "quality_score": round(quality_score, 2),
            "quality_adjustment": round(adjustment, 2),
            "estimated_mfe_pct": round(mfe, 3),
            "estimated_mae_pct": round(mae, 3),
            "mfe_mae_ratio": round(ratio, 2),
            "ev_after_quality": ev_after_quality,
            "quality_reasons": reasons[:8],
            "quality_fail_reasons": fails[:8],
            "min_quality_ev": min_quality_ev,
            "min_mfe_mae_ratio": min_mfe_mae_ratio,
        }
