from intraday_label_engine import IntradayLabelEngine
from intraday_signal_engine import IntradaySignalEngine


class DecisionEngine:
    """
    成本感知決策引擎。

    重點：
    1. 有建立近 30 日當沖模型時，優先使用模型。
    2. 模型必須預測「扣成本後期望值 > 0」才放行。
    3. 勝率必須高於該停損 / 停利 / 成本組合的損益兩平勝率。
    4. 沒有模型時才回退一般 AI，但一般 AI 會更保守。
    """

    COST_PCT = 0.435
    DEFAULT_STOP_PCT = 0.7
    DEFAULT_TAKE_PCT = 1.8
    DEFAULT_MAX_HOLD_BARS = 50
    MIN_EXPECTED_VALUE = 0.04

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
    def _base_wait(price, score, title, reason, extra=None):
        payload = {
            "action": "WAIT",
            "score": int(max(0, min(100, score))),
            "title": title,
            "reason": reason,
            "reasons": [reason],
            "entry_price": price,
            "entry": price,
            "stop_loss": 0,
            "take_profit": 0,
            "risk_reward": 0,
            "rr": 0,
            "rebound": 50,
            "multi_period_status": "WAIT",
            "multi_period": {},
            "swing_state": "等待確認",
            "swing_prediction": {},
            "predicted_up_pct": 0,
            "predicted_down_pct": 0,
            "long_rr": 0,
            "short_rr": 0,
            "risk_level": "HIGH",
            "expected_value": 0,
            "predicted_win_rate": 0,
            "required_win_rate": 0,
        }

        if extra:
            payload.update(extra)

        return payload

    @staticmethod
    def _fallback_from_ai(ai, price, prices, volumes):
        ai = ai or {}
        action = str(ai.get("signal", "WAIT") or "WAIT").upper()
        score = DecisionEngine._safe_int(ai.get("score", 0), 0)
        rebound = ai.get("rebound_prob", 50)
        reasons = ai.get("reasons") or ai.get("reason") or []

        if isinstance(reasons, str):
            reasons = [reasons]

        if not reasons:
            reasons = ["尚未建立近 30 日當沖模型，使用一般 AI 備援。"]

        if len(prices or []) < 20:
            return DecisionEngine._base_wait(
                price=price,
                score=min(score, 35),
                title="等待盤中資料",
                reason="至少需要 20 根盤中資料才能判斷。",
            )

        if action not in ["BUY", "SELL"]:
            return DecisionEngine._base_wait(
                price=price,
                score=score,
                title="一般 AI 觀望",
                reason="一般 AI 尚未出現明確多空訊號。",
                extra={"reasons": reasons, "rebound": rebound},
            )

        # 沒有模型時，分數要更高才允許，避免尚未成本感知就亂出手。
        if score < 75:
            return DecisionEngine._base_wait(
                price=price,
                score=score,
                title="備援訊號風險偏高",
                reason="尚未建立成本感知模型，且一般 AI 分數低於 75，暫不出手。",
                extra={"reasons": reasons, "rebound": rebound},
            )

        stop_pct = DecisionEngine.DEFAULT_STOP_PCT
        take_pct = DecisionEngine.DEFAULT_TAKE_PCT
        risk_reward = take_pct / max(stop_pct, 0.01)

        if action == "BUY":
            stop_loss = price * (1 - stop_pct / 100)
            take_profit = price * (1 + take_pct / 100)
            title = "一般 AI 做多"
            reason = "尚未建立當沖模型，僅使用高分一般 AI 多方訊號。"
            multi_period_status = "BULL_STRONG"
            predicted_up_pct = take_pct
            predicted_down_pct = 0
        else:
            stop_loss = price * (1 + stop_pct / 100)
            take_profit = price * (1 - take_pct / 100)
            title = "一般 AI 做空"
            reason = "尚未建立當沖模型，僅使用高分一般 AI 空方訊號。"
            multi_period_status = "BEAR_STRONG"
            predicted_up_pct = 0
            predicted_down_pct = take_pct

        reasons = [
            "備援模式：尚未套用近 30 日相似 K 線模型。",
            "建議先在左側建立當沖模型，再以成本感知訊號為主。",
        ] + reasons[:5]

        return {
            "action": action,
            "score": int(max(0, min(100, score))),
            "title": title,
            "reason": reason,
            "reasons": reasons,
            "entry_price": price,
            "entry": round(price, 2),
            "stop_loss": round(stop_loss, 2),
            "take_profit": round(take_profit, 2),
            "risk_reward": round(risk_reward, 2),
            "rr": round(risk_reward, 2),
            "adaptive_stop_pct": round(stop_pct, 3),
            "adaptive_take_pct": round(take_pct, 3),
            "rebound": rebound,
            "multi_period_status": multi_period_status,
            "multi_period": {},
            "swing_state": "一般 AI 備援模式",
            "swing_prediction": {
                "mode": "fallback_ai",
                "ai_signal": action,
                "ai_score": score,
                "note": "尚未建立近 30 日模型，風險較高。",
            },
            "predicted_up_pct": predicted_up_pct,
            "predicted_down_pct": predicted_down_pct,
            "long_rr": round(risk_reward, 2),
            "short_rr": round(risk_reward, 2),
            "risk_level": "MEDIUM",
            "expected_value": 0,
            "predicted_win_rate": 0,
            "required_win_rate": 0,
            "model_label_rows": 0,
        }

    @staticmethod
    def _build_trade_payload(action, price, score, prediction, model_package):
        stop_pct = float(model_package.get("stop_pct", DecisionEngine.DEFAULT_STOP_PCT))
        take_pct = float(model_package.get("take_pct", DecisionEngine.DEFAULT_TAKE_PCT))
        cost_pct = float(model_package.get("cost_pct", DecisionEngine.COST_PCT))

        chosen = prediction.get("chosen", {}) or {}
        buy = prediction.get("buy", {}) or {}
        sell = prediction.get("sell", {}) or {}

        expected_value = DecisionEngine._safe_float(chosen.get("expected_value"), 0)
        predicted_win_rate = DecisionEngine._safe_float(chosen.get("win_rate"), 0)
        required_win_rate = DecisionEngine._safe_float(prediction.get("required_win_rate"), 0)
        sample_count = DecisionEngine._safe_int(chosen.get("sample_count"), 0)
        profit_factor = DecisionEngine._safe_float(chosen.get("profit_factor"), 0)

        if action == "BUY":
            stop_loss = price * (1 - stop_pct / 100)
            take_profit = price * (1 + take_pct / 100)
            risk_reward = take_pct / max(stop_pct, 0.01)
            title = "成本感知模型做多"
            reason = (
                f"BUY 校準後勝率 {predicted_win_rate:.1f}% ≥ 需求 {required_win_rate:.1f}%，"
                f"扣成本期望 {expected_value:.3f}%。"
            )
            reasons = [
                buy.get("reason", ""),
                f"SELL 扣成本期望 {sell.get('expected_value', 0)}%",
                f"BUY 樣本數 {sample_count}，Profit Factor {profit_factor:.2f}",
                f"型態：{chosen.get('setup_type', '未分類')}｜濾網折扣 {chosen.get('filter_penalty', 0)}%",
                *(chosen.get("professional_filters", [])[:3]),
                f"停損 {stop_pct:.1f}%｜停利 {take_pct:.1f}%｜成本約 {cost_pct:.3f}%",
                f"模型區間 {model_package.get('start_date')} ~ {model_package.get('end_date')}",
            ]
            multi_period_status = "MODEL_BULL"
            swing_state = "正期望偏多"
            predicted_up_pct = take_pct
            predicted_down_pct = 0
        else:
            stop_loss = price * (1 + stop_pct / 100)
            take_profit = price * (1 - take_pct / 100)
            risk_reward = take_pct / max(stop_pct, 0.01)
            title = "成本感知模型做空"
            reason = (
                f"SELL 校準後勝率 {predicted_win_rate:.1f}% ≥ 需求 {required_win_rate:.1f}%，"
                f"扣成本期望 {expected_value:.3f}%。"
            )
            reasons = [
                sell.get("reason", ""),
                f"BUY 扣成本期望 {buy.get('expected_value', 0)}%",
                f"SELL 樣本數 {sample_count}，Profit Factor {profit_factor:.2f}",
                f"型態：{chosen.get('setup_type', '未分類')}｜濾網折扣 {chosen.get('filter_penalty', 0)}%",
                *(chosen.get("professional_filters", [])[:3]),
                f"停損 {stop_pct:.1f}%｜停利 {take_pct:.1f}%｜成本約 {cost_pct:.3f}%",
                f"模型區間 {model_package.get('start_date')} ~ {model_package.get('end_date')}",
            ]
            multi_period_status = "MODEL_BEAR"
            swing_state = "正期望偏空"
            predicted_up_pct = 0
            predicted_down_pct = take_pct

        return {
            "action": action,
            "score": int(max(0, min(100, score))),
            "title": title,
            "reason": reason,
            "reasons": [r for r in reasons if r],
            "entry_price": price,
            "entry": round(price, 2),
            "stop_loss": round(stop_loss, 2),
            "take_profit": round(take_profit, 2),
            "risk_reward": round(risk_reward, 2),
            "rr": round(risk_reward, 2),
            "rebound": 55 if action == "BUY" else 45,
            "multi_period_status": multi_period_status,
            "multi_period": {},
            "swing_state": swing_state,
            "swing_prediction": prediction,
            "predicted_up_pct": predicted_up_pct,
            "predicted_down_pct": predicted_down_pct,
            "long_rr": round(risk_reward, 2),
            "short_rr": round(risk_reward, 2),
            "risk_level": prediction.get("risk_level", "NORMAL"),
            "expected_value": round(expected_value, 3),
            "predicted_win_rate": round(predicted_win_rate, 2),
            "required_win_rate": round(required_win_rate, 2),
            "model_start_date": model_package.get("start_date", ""),
            "model_end_date": model_package.get("end_date", ""),
            "model_label_rows": model_package.get("label_rows", 0),
        }


    @staticmethod
    def _payload_from_realtime_signal(signal, price):
        action = signal.get("decision", "WAIT")
        chosen = signal.get("chosen", {}) or {}
        risk_plan = signal.get("risk_plan", {}) or {}
        stop_pct = DecisionEngine._safe_float(signal.get("adaptive_stop_pct") or risk_plan.get("stop_pct"), DecisionEngine.DEFAULT_STOP_PCT)
        take_pct = DecisionEngine._safe_float(signal.get("adaptive_take_pct") or risk_plan.get("take_pct"), DecisionEngine.DEFAULT_TAKE_PCT)
        if stop_pct <= 0:
            stop_pct = DecisionEngine.DEFAULT_STOP_PCT
        if take_pct <= 0:
            take_pct = DecisionEngine.DEFAULT_TAKE_PCT
        risk_reward = take_pct / max(stop_pct, 0.01)

        if action not in ["BUY", "SELL"]:
            return DecisionEngine._base_wait(
                price=price,
                score=signal.get("score", 45),
                title=signal.get("title", "即時結構觀望"),
                reason=signal.get("reason", "當下量價結構尚未達到扣成本後正期望。"),
                extra={
                    "reasons": signal.get("reasons", []),
                    "swing_prediction": signal,
                    "risk_level": "HIGH",
                    "expected_value": chosen.get("expected_value", 0),
                    "predicted_win_rate": chosen.get("win_rate", 0),
                    "required_win_rate": signal.get("required_win_rate", 0),
                    "estimated_mfe_pct": signal.get("estimated_mfe_pct", 0),
                    "estimated_mae_pct": signal.get("estimated_mae_pct", 0),
                    "mfe_mae_ratio": signal.get("mfe_mae_ratio", 0),
                    "ev_after_quality": signal.get("ev_after_quality", 0),
                },
            )

        if action == "BUY":
            stop_loss = price * (1 - stop_pct / 100)
            take_profit = price * (1 + take_pct / 100)
            status = "STRUCTURE_BULL"
            rebound = 58
            predicted_up_pct = take_pct
            predicted_down_pct = 0
        else:
            stop_loss = price * (1 + stop_pct / 100)
            take_profit = price * (1 - take_pct / 100)
            status = "STRUCTURE_BEAR"
            rebound = 42
            predicted_up_pct = 0
            predicted_down_pct = take_pct

        return {
            "action": action,
            "score": int(max(0, min(100, signal.get("score", 0)))),
            "title": signal.get("title", "即時結構 AI 訊號"),
            "reason": signal.get("reason", ""),
            "reasons": signal.get("reasons", []),
            "entry_price": price,
            "entry": round(price, 2),
            "stop_loss": round(stop_loss, 2),
            "take_profit": round(take_profit, 2),
            "risk_reward": round(risk_reward, 2),
            "rr": round(risk_reward, 2),
            "adaptive_stop_pct": round(stop_pct, 3),
            "adaptive_take_pct": round(take_pct, 3),
            "rebound": rebound,
            "multi_period_status": status,
            "multi_period": {},
            "swing_state": "即時結構 AI",
            "swing_prediction": signal,
            "predicted_up_pct": predicted_up_pct,
            "predicted_down_pct": predicted_down_pct,
            "long_rr": round(risk_reward, 2),
            "short_rr": round(risk_reward, 2),
            "risk_level": signal.get("risk_level", "NORMAL"),
            "expected_value": chosen.get("expected_value", 0),
            "predicted_win_rate": chosen.get("win_rate", 0),
            "required_win_rate": signal.get("required_win_rate", 0),
            "estimated_mfe_pct": signal.get("estimated_mfe_pct", 0),
            "estimated_mae_pct": signal.get("estimated_mae_pct", 0),
            "mfe_mae_ratio": signal.get("mfe_mae_ratio", 0),
            "ev_after_quality": signal.get("ev_after_quality", chosen.get("ev_after_quality", 0)),
            "signal_quality": signal.get("signal_quality", {}),
            "streak_volume": signal.get("streak_volume", {}),
            "trade_management_note": "進場後若 3~5 根K未推進或浮盈回吐，系統會提示提早退出。",
            "rest_microstructure": signal.get("rest_microstructure", {}),
            "estimated_slippage_pct": signal.get("estimated_slippage_pct", 0),
            "execution_risk": signal.get("execution_risk", ""),
            "model_label_rows": 0,
            "model_start_date": "即時結構",
            "model_end_date": "不訓練",
        }

    @staticmethod
    def generate(
        ai,
        price,
        vwap,
        ema5,
        ema20,
        ema60,
        rsi,
        macd,
        macd_signal,
        bid_ratio,
        prices,
        volumes,
        opens=None,
        highs=None,
        lows=None,
        vwap_values=None,
        time_values=None,
        bids=None,
        asks=None,
        rest_microstructure=None,
    ):
        ai = ai or {}
        price = DecisionEngine._safe_float(price)

        if price <= 0:
            return DecisionEngine._base_wait(
                price=price,
                score=0,
                title="價格異常",
                reason="目前價格小於等於 0，無法判斷。",
            )

        prices = prices or []
        volumes = volumes or []
        opens = opens or prices
        highs = highs or prices
        lows = lows or prices
        vwap_values = vwap_values or []
        time_values = time_values or []
        model_package = ai.get("intraday_model_package")

        if not model_package:
            signal = IntradaySignalEngine.analyze(
                prices=prices,
                volumes=volumes,
                opens=opens,
                highs=highs,
                lows=lows,
                vwap_values=vwap_values,
                time_values=time_values,
                bids=bids,
                asks=asks,
                rest_microstructure=rest_microstructure,
                stop_pct=DecisionEngine.DEFAULT_STOP_PCT,
                take_pct=DecisionEngine.DEFAULT_TAKE_PCT,
                cost_pct=DecisionEngine.COST_PCT,
                min_score=64,
                min_expected_value=0.02,
            )
            if signal.get("decision") in ["BUY", "SELL"]:
                return DecisionEngine._payload_from_realtime_signal(signal, price)
            return DecisionEngine._fallback_from_ai(ai=ai, price=price, prices=prices, volumes=volumes)

        model = model_package.get("model")
        if model is None:
            signal = IntradaySignalEngine.analyze(
                prices=prices,
                volumes=volumes,
                opens=opens,
                highs=highs,
                lows=lows,
                vwap_values=vwap_values,
                time_values=time_values,
                bids=bids,
                asks=asks,
                rest_microstructure=rest_microstructure,
                stop_pct=DecisionEngine.DEFAULT_STOP_PCT,
                take_pct=DecisionEngine.DEFAULT_TAKE_PCT,
                cost_pct=DecisionEngine.COST_PCT,
                min_score=64,
                min_expected_value=0.02,
            )
            if signal.get("decision") in ["BUY", "SELL"]:
                return DecisionEngine._payload_from_realtime_signal(signal, price)
            return DecisionEngine._fallback_from_ai(ai=ai, price=price, prices=prices, volumes=volumes)

        if len(prices) < 20:
            return DecisionEngine._base_wait(
                price=price,
                score=30,
                title="等待盤中資料",
                reason="模型模式至少需要 20 根盤中資料才能比對相似情境。",
                extra={
                    "model_start_date": model_package.get("start_date", ""),
                    "model_end_date": model_package.get("end_date", ""),
                    "model_label_rows": model_package.get("label_rows", 0),
                },
            )

        feature = IntradayLabelEngine.extract_current_features(prices=prices, volumes=volumes)
        if feature is None:
            return DecisionEngine._fallback_from_ai(ai=ai, price=price, prices=prices, volumes=volumes)

        stop_pct = DecisionEngine._safe_float(model_package.get("stop_pct"), DecisionEngine.DEFAULT_STOP_PCT)
        take_pct = DecisionEngine._safe_float(model_package.get("take_pct"), DecisionEngine.DEFAULT_TAKE_PCT)
        cost_pct = DecisionEngine._safe_float(model_package.get("cost_pct"), DecisionEngine.COST_PCT)

        prediction = model.predict(
            feature=feature,
            min_expected_value=DecisionEngine.MIN_EXPECTED_VALUE,
            min_win_rate=None,
            min_sample_count=20,
            stop_pct=stop_pct,
            take_pct=take_pct,
            cost_pct=cost_pct,
            safety_margin=2.0,
            use_professional_filters=True,
        )

        decision = prediction.get("decision", "WAIT")
        score = int(prediction.get("score", 50))
        buy = prediction.get("buy", {}) or {}
        sell = prediction.get("sell", {}) or {}
        chosen = prediction.get("chosen", {}) or {}

        if decision == "BUY":
            return DecisionEngine._build_trade_payload(
                action="BUY",
                price=price,
                score=score,
                prediction=prediction,
                model_package=model_package,
            )

        if decision == "SELL":
            return DecisionEngine._build_trade_payload(
                action="SELL",
                price=price,
                score=score,
                prediction=prediction,
                model_package=model_package,
            )

        realtime_signal = IntradaySignalEngine.analyze(
            prices=prices,
            volumes=volumes,
            opens=opens,
            highs=highs,
            lows=lows,
            vwap_values=vwap_values,
            time_values=time_values,
            bids=bids,
            asks=asks,
            rest_microstructure=rest_microstructure,
            stop_pct=stop_pct,
            take_pct=take_pct,
            cost_pct=cost_pct,
            min_score=66,
            min_expected_value=0.02,
        )
        if realtime_signal.get("decision") in ["BUY", "SELL"]:
            payload = DecisionEngine._payload_from_realtime_signal(realtime_signal, price)
            payload["reasons"] = ["歷史相似模型未放行，但即時結構 AI 達標。"] + payload.get("reasons", [])[:6]
            return payload

        wait_reasons = [
            f"BUY 校準勝率 {buy.get('win_rate', 0)}%，原始 {buy.get('raw_win_rate', 0)}%，EV {buy.get('expected_value', 0)}%",
            f"SELL 校準勝率 {sell.get('win_rate', 0)}%，原始 {sell.get('raw_win_rate', 0)}%，EV {sell.get('expected_value', 0)}%",
            f"需求勝率 {prediction.get('required_win_rate', 0)}%，最低期望 {prediction.get('min_expected_value', 0)}%",
            f"目前最佳方向 {chosen.get('action', '無')}，型態 {chosen.get('setup_type', '未分類')}，濾網折扣 {chosen.get('filter_penalty', 0)}%",
            *(chosen.get("hard_fail_reasons", [])[:3]),
            *(chosen.get("professional_filters", [])[:3]),
            "判斷：此次交易風險高，不出手。",
        ]

        return DecisionEngine._base_wait(
            price=price,
            score=score,
            title="專業濾網未通過",
            reason="扣成本後期望值、校準勝率或 ORB / VWAP / 量能濾網不足，暫不出手。",
            extra={
                "reasons": wait_reasons,
                "swing_prediction": prediction,
                "risk_level": "HIGH",
                "expected_value": chosen.get("expected_value", 0),
                "predicted_win_rate": chosen.get("win_rate", 0),
                "required_win_rate": prediction.get("required_win_rate", 0),
                "model_start_date": model_package.get("start_date", ""),
                "model_end_date": model_package.get("end_date", ""),
                "model_label_rows": model_package.get("label_rows", 0),
            },
        )
