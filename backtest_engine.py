import math
import time
import requests
from datetime import datetime
from collections import defaultdict

import pandas as pd

from market_analyzer import MarketAnalyzer
from ai_predictor import AIPredictor
from decision_engine import DecisionEngine
from multi_period_engine import MultiPeriodEngine
from intraday_label_engine import IntradayLabelEngine
from intraday_signal_engine import IntradaySignalEngine
from trade_management_engine import TradeManagementEngine

try:
    from stock_model_cache import StockModelCache
except Exception:
    StockModelCache = None


class BacktestEngine:
    BASE_URL = "https://api.fugle.tw/marketdata/v1.0/stock"

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
    def _to_datetime(value):
        if isinstance(value, datetime):
            return value

        try:
            return datetime.fromisoformat(str(value))
        except Exception:
            return None

    @staticmethod
    def fetch_historical_candles(api_key, symbol, timeframe="1"):
        url = f"{BacktestEngine.BASE_URL}/historical/candles/{symbol}"
        headers = {"X-API-KEY": api_key}
        params = {
            "timeframe": str(timeframe),
            "fields": "open,high,low,close,volume",
            "sort": "asc",
        }

        response = requests.get(url, headers=headers, params=params, timeout=25)

        if response.status_code == 401:
            raise RuntimeError("API KEY 無效或權限不足。")
        if response.status_code == 429:
            raise RuntimeError("API 請求過多，請稍後再試。")
        if response.status_code >= 400:
            raise RuntimeError(f"Fugle historical candles error: {response.status_code}")

        payload = response.json()
        raw_data = payload.get("data", [])

        if not isinstance(raw_data, list):
            raise RuntimeError("Fugle 回傳格式異常：data 不是 list。")

        candles = []
        for item in raw_data:
            dt = BacktestEngine._to_datetime(item.get("date"))
            if dt is None:
                continue

            open_price = BacktestEngine._safe_float(item.get("open"))
            high_price = BacktestEngine._safe_float(item.get("high"))
            low_price = BacktestEngine._safe_float(item.get("low"))
            close_price = BacktestEngine._safe_float(item.get("close"))
            volume = BacktestEngine._safe_float(item.get("volume"))

            if close_price <= 0:
                continue

            candles.append(
                {
                    "time": dt,
                    "date": dt.date().isoformat(),
                    "open": open_price,
                    "high": high_price,
                    "low": low_price,
                    "close": close_price,
                    "volume": volume,
                }
            )

        return sorted(candles, key=lambda x: x["time"])

    @staticmethod
    def _candles_to_dataframe(candles):
        rows = []
        for c in candles:
            rows.append(
                {
                    "date": c.get("time"),
                    "open": c.get("open"),
                    "high": c.get("high"),
                    "low": c.get("low"),
                    "close": c.get("close"),
                    "volume": c.get("volume"),
                }
            )
        return pd.DataFrame(rows)

    @staticmethod
    def _group_by_day(candles):
        days = defaultdict(list)
        for candle in candles:
            days[candle["date"]].append(candle)
        return dict(days)

    @staticmethod
    def _select_days(days, day_scope):
        valid_days = []
        for day in sorted(days.keys()):
            day_candles = days[day]
            if len(day_candles) >= 40:
                valid_days.append({"date": day, "candles": day_candles})

        if not valid_days:
            return []

        if day_scope == "last_open_day":
            return [valid_days[-1]]
        if day_scope == "recent_5_days":
            return valid_days[-5:]
        return valid_days

    @staticmethod
    def _build_series(candles):
        prices = []
        volumes = []
        vwaps = []
        times = []
        cum_amount = 0.0
        cum_volume = 0.0

        for c in candles:
            price = BacktestEngine._safe_float(c.get("close"))
            volume = BacktestEngine._safe_float(c.get("volume"))
            cum_amount += price * volume
            cum_volume += volume
            vwap = cum_amount / max(cum_volume, 1)
            prices.append(price)
            volumes.append(volume)
            vwaps.append(vwap)
            times.append(c.get("time"))

        return prices, volumes, vwaps, times

    @staticmethod
    def _build_ohlcv_series(candles):
        opens = []
        highs = []
        lows = []
        prices = []
        volumes = []
        vwaps = []
        times = []
        cum_amount = 0.0
        cum_volume = 0.0

        for c in candles:
            open_price = BacktestEngine._safe_float(c.get("open"))
            high_price = BacktestEngine._safe_float(c.get("high"))
            low_price = BacktestEngine._safe_float(c.get("low"))
            close_price = BacktestEngine._safe_float(c.get("close"))
            volume = BacktestEngine._safe_float(c.get("volume"))
            cum_amount += close_price * volume
            cum_volume += volume
            vwap = cum_amount / max(cum_volume, 1)
            opens.append(open_price if open_price > 0 else close_price)
            highs.append(high_price if high_price > 0 else close_price)
            lows.append(low_price if low_price > 0 else close_price)
            prices.append(close_price)
            volumes.append(volume)
            vwaps.append(vwap)
            times.append(c.get("time"))

        return opens, highs, lows, prices, volumes, vwaps, times

    @staticmethod
    def _make_decision(
        candles,
        model_package=None,
        use_multi_period=False,
        require_resonance=False,
    ):
        prices, volumes, vwaps, times = BacktestEngine._build_series(candles)
        return BacktestEngine._make_decision_from_series(
            prices=prices,
            volumes=volumes,
            vwaps=vwaps,
            times=times,
            model_package=model_package,
            use_multi_period=use_multi_period,
            require_resonance=require_resonance,
        )

    @staticmethod
    def _make_decision_from_series(
        prices,
        volumes,
        vwaps,
        times,
        model_package=None,
        use_multi_period=False,
        require_resonance=False,
        use_realtime_signal=False,
        opens=None,
        highs=None,
        lows=None,
        stop_pct=0.7,
        take_pct=1.8,
        cost_pct=0.435,
    ):
        """
        回測用快速決策。

        原本每一根 K 都會重建 current_candles、重算 VWAP、跑一般 AI、跑多週期，
        Walk-forward 近 30 日會非常慢。

        這版在有成本感知模型時，直接走 DecisionEngine 的模型路徑：
        - 不先跑一般 AIPredictor
        - 預設不跑 MultiPeriodEngine
        - 只有勾選「只測多週期共振」時才計算多週期參考

        這不會偷看未來，因為傳入的 prices/volumes 仍然只到目前這一根 K。
        """

        if len(prices) < 20:
            return None

        price = prices[-1]
        vwap = vwaps[-1] if vwaps else price

        if use_realtime_signal:
            signal = IntradaySignalEngine.analyze(
                prices=prices,
                volumes=volumes,
                opens=opens,
                highs=highs,
                lows=lows,
                vwap_values=vwaps,
                time_values=times,
                stop_pct=stop_pct,
                take_pct=take_pct,
                cost_pct=cost_pct,
                min_score=60,
                min_expected_value=0.00,
            )
            action = signal.get("decision", "WAIT")
            chosen = signal.get("chosen", {}) or {}
            risk_plan = signal.get("risk_plan", {}) or {}
            eff_stop_pct = BacktestEngine._safe_float(signal.get("adaptive_stop_pct") or risk_plan.get("stop_pct"), stop_pct)
            eff_take_pct = BacktestEngine._safe_float(signal.get("adaptive_take_pct") or risk_plan.get("take_pct"), take_pct)
            if action in ["BUY", "SELL"]:
                stop_rate = eff_stop_pct / 100
                take_rate = eff_take_pct / 100
                if action == "BUY":
                    stop_loss = price * (1 - stop_rate)
                    take_profit = price * (1 + take_rate)
                    status = "STRUCTURE_BULL"
                else:
                    stop_loss = price * (1 + stop_rate)
                    take_profit = price * (1 - take_rate)
                    status = "STRUCTURE_BEAR"
                return {
                    "action": action,
                    "score": signal.get("score", 0),
                    "title": signal.get("title", "即時結構 AI 訊號"),
                    "reason": signal.get("reason", ""),
                    "reasons": signal.get("reasons", []),
                    "entry_price": price,
                    "entry": round(price, 2),
                    "stop_loss": round(stop_loss, 2),
                    "take_profit": round(take_profit, 2),
                    "risk_reward": round(eff_take_pct / max(eff_stop_pct, 0.01), 2),
                    "rr": round(eff_take_pct / max(eff_stop_pct, 0.01), 2),
                    "adaptive_stop_pct": round(eff_stop_pct, 3),
                    "adaptive_take_pct": round(eff_take_pct, 3),
                    "rebound": 55 if action == "BUY" else 45,
                    "multi_period_status": status,
                    "multi_period": {},
                    "swing_state": "即時結構 AI",
                    "swing_prediction": {
                        "mode": "realtime_structure_no_training",
                        "buy": signal.get("buy", {}),
                        "sell": signal.get("sell", {}),
                        "chosen": chosen,
                        "required_win_rate": signal.get("required_win_rate", 0),
                        "risk_plan": risk_plan,
                        "tape_flow": signal.get("tape_flow", {}),
                        "streak_volume": signal.get("streak_volume", {}),
                        "orderbook_flow": signal.get("orderbook_flow", {}),
                        "market_context": signal.get("market_context", {}),
                        "feature": signal.get("feature", {}),
                    },
                    "predicted_up_pct": eff_take_pct if action == "BUY" else 0,
                    "predicted_down_pct": eff_take_pct if action == "SELL" else 0,
                    "long_rr": round(eff_take_pct / max(eff_stop_pct, 0.01), 2),
                    "short_rr": round(eff_take_pct / max(eff_stop_pct, 0.01), 2),
                    "risk_level": signal.get("risk_level", "NORMAL"),
                    "expected_value": chosen.get("expected_value", 0),
                    "predicted_win_rate": chosen.get("win_rate", 0),
                    "required_win_rate": signal.get("required_win_rate", 0),
                    "estimated_mfe_pct": signal.get("estimated_mfe_pct", chosen.get("estimated_mfe_pct", 0)),
                    "estimated_mae_pct": signal.get("estimated_mae_pct", chosen.get("estimated_mae_pct", 0)),
                    "mfe_mae_ratio": signal.get("mfe_mae_ratio", chosen.get("mfe_mae_ratio", 0)),
                    "ev_after_quality": signal.get("ev_after_quality", chosen.get("ev_after_quality", 0)),
                    "signal_quality": signal.get("signal_quality", {}),
                    "model_label_rows": 0,
                }
            return {
                "action": "WAIT",
                "score": signal.get("score", 0),
                "title": signal.get("title", "即時結構未達出手標準"),
                "reason": signal.get("reason", ""),
                "reasons": signal.get("reasons", []),
                "entry_price": price,
                "entry": round(price, 2),
                "stop_loss": 0,
                "take_profit": 0,
                "risk_reward": 0,
                "rr": 0,
                "rebound": 50,
                "multi_period_status": "WAIT",
                "multi_period": {},
                "swing_state": "即時結構觀望",
                "swing_prediction": {
                    "mode": "realtime_structure_no_training",
                    "buy": signal.get("buy", {}),
                    "sell": signal.get("sell", {}),
                    "chosen": signal.get("chosen", {}),
                    "required_win_rate": signal.get("required_win_rate", 0),
                    "streak_volume": signal.get("streak_volume", {}),
                    "feature": signal.get("feature", {}),
                },
                "risk_level": "HIGH",
                "expected_value": (signal.get("chosen", {}) or {}).get("expected_value", 0),
                "predicted_win_rate": (signal.get("chosen", {}) or {}).get("win_rate", 0),
                "required_win_rate": signal.get("required_win_rate", 0),
                "estimated_mfe_pct": signal.get("estimated_mfe_pct", 0),
                "estimated_mae_pct": signal.get("estimated_mae_pct", 0),
                "mfe_mae_ratio": signal.get("mfe_mae_ratio", 0),
                "ev_after_quality": signal.get("ev_after_quality", 0),
            }

        # 成本感知模型模式：直接讓 DecisionEngine 用模型判斷，避免每根 K 都跑一般 AI。
        if model_package is not None:
            ai = {
                "signal": "WAIT",
                "score": 50,
                "rebound_prob": 50,
                "reasons": ["回測快速模式：使用成本感知模型，未使用一般 AI 預判。"],
                "intraday_model_package": model_package,
            }

            decision = DecisionEngine.generate(
                ai=ai,
                price=price,
                vwap=vwap,
                ema5=0,
                ema20=0,
                ema60=0,
                rsi=50,
                macd=0,
                macd_signal=0,
                bid_ratio=1.0,
                prices=prices,
                volumes=volumes,
                opens=opens,
                highs=highs,
                lows=lows,
                vwap_values=vwaps,
                time_values=times,
            )

            if not use_multi_period and not require_resonance:
                return decision

            multi_period = MultiPeriodEngine.analyze(
                prices=prices,
                volumes=volumes,
                vwap_values=vwaps,
                time_values=times,
            )

            decision["multi_period"] = multi_period
            decision["multi_period_reference_status"] = multi_period.get("status", "")

            reasons = list(decision.get("reasons", []))
            reasons.insert(0, f"多週期參考：{multi_period.get('status', '未知')}｜模型以扣成本期望為主")
            decision["reasons"] = reasons[:8]

            return decision

        # 一般 AI 模式：保留原本指標與多週期判斷。
        ema5 = MarketAnalyzer.calculate_ema(prices, 5)
        ema20 = MarketAnalyzer.calculate_ema(prices, 20)
        ema60 = MarketAnalyzer.calculate_ema(prices, 60)
        rsi = MarketAnalyzer.calculate_rsi(prices)
        macd, macd_signal, _ = MarketAnalyzer.calculate_macd(prices)
        momentum = MarketAnalyzer.momentum(prices)
        bid_ratio = 1.0

        ai = AIPredictor.predict_trade(
            prices,
            volumes,
            ema5,
            ema20,
            ema60,
            rsi,
            macd,
            macd_signal,
            momentum,
            bid_ratio=bid_ratio,
            vwap=vwap,
        )

        decision = DecisionEngine.generate(
            ai=ai,
            price=price,
            vwap=vwap,
            ema5=ema5,
            ema20=ema20,
            ema60=ema60,
            rsi=rsi,
            macd=macd,
            macd_signal=macd_signal,
            bid_ratio=bid_ratio,
            prices=prices,
            volumes=volumes,
        )

        multi_period = MultiPeriodEngine.analyze(
            prices=prices,
            volumes=volumes,
            vwap_values=vwaps,
            time_values=times,
        )

        return MultiPeriodEngine.apply_to_decision(decision=decision, multi_period=multi_period)


    @staticmethod
    def _simulate_exit(
        action,
        entry_price,
        entry_index,
        day_candles,
        decision,
        max_hold_bars=50,
        default_stop_pct=0.7,
        default_take_pct=1.8,
        commission_rate_pct=0.1425,
        commission_discount=1.0,
        tax_rate_pct=0.15,
    ):
        default_stop_pct = BacktestEngine._safe_float(default_stop_pct, 0.6)
        default_take_pct = BacktestEngine._safe_float(default_take_pct, 2.0)
        commission_rate_pct = BacktestEngine._safe_float(commission_rate_pct, 0.1425)
        commission_discount = BacktestEngine._safe_float(commission_discount, 1.0)
        tax_rate_pct = BacktestEngine._safe_float(tax_rate_pct, 0.15)
        effective_commission_pct = commission_rate_pct * commission_discount

        decision = decision or {}
        stop_loss_pct = BacktestEngine._safe_float(decision.get("adaptive_stop_pct"), default_stop_pct)
        take_profit_pct = BacktestEngine._safe_float(decision.get("adaptive_take_pct"), default_take_pct)
        if stop_loss_pct <= 0:
            stop_loss_pct = default_stop_pct
        if take_profit_pct <= 0:
            take_profit_pct = default_take_pct

        stop_rate = stop_loss_pct / 100
        take_rate = take_profit_pct / 100

        if action == "BUY":
            stop_loss = entry_price * (1 - stop_rate)
            take_profit = entry_price * (1 + take_rate)
        elif action == "SELL":
            stop_loss = entry_price * (1 + stop_rate)
            take_profit = entry_price * (1 - take_rate)
        else:
            stop_loss = entry_price
            take_profit = entry_price
            stop_loss_pct = 0
            take_profit_pct = 0

        exit_price = entry_price
        exit_reason = "時間出場"
        exit_index = min(len(day_candles) - 1, entry_index + max_hold_bars)
        end_index = min(len(day_candles) - 1, entry_index + max_hold_bars)
        best_favorable_pct = 0.0

        for i in range(entry_index + 1, end_index + 1):
            c = day_candles[i]
            high = BacktestEngine._safe_float(c.get("high"))
            low = BacktestEngine._safe_float(c.get("low"))
            close = BacktestEngine._safe_float(c.get("close"))

            if action == "BUY":
                if low <= stop_loss:
                    exit_price = stop_loss
                    exit_reason = "停損"
                    exit_index = i
                    break
                if high >= take_profit:
                    exit_price = take_profit
                    exit_reason = "停利"
                    exit_index = i
                    break
            elif action == "SELL":
                if high >= stop_loss:
                    exit_price = stop_loss
                    exit_reason = "停損"
                    exit_index = i
                    break
                if low <= take_profit:
                    exit_price = take_profit
                    exit_reason = "停利"
                    exit_index = i
                    break

            # 進場後管理：方向沒有推進、浮盈回吐、或反向K明顯時提前退出。
            management = TradeManagementEngine.check_exit(
                action=action,
                entry_price=entry_price,
                current_candle=c,
                bars_held=max(0, i - entry_index),
                best_favorable_pct=best_favorable_pct,
            )
            if management:
                best_favorable_pct = management.get("best_favorable_pct", best_favorable_pct)
                if management.get("exit"):
                    exit_price = management.get("exit_price", close)
                    exit_reason = management.get("reason", "進場後管理出場")
                    exit_index = i
                    break

            exit_price = close
            exit_index = i

        if action == "BUY":
            gross_pnl_pct = (exit_price - entry_price) / entry_price * 100
            buy_commission_pct = effective_commission_pct
            sell_commission_pct = effective_commission_pct * (exit_price / entry_price)
            sell_tax_pct = tax_rate_pct * (exit_price / entry_price)
            cost_pct = buy_commission_pct + sell_commission_pct + sell_tax_pct
        else:
            gross_pnl_pct = (entry_price - exit_price) / entry_price * 100
            sell_commission_pct = effective_commission_pct
            sell_tax_pct = tax_rate_pct
            buyback_commission_pct = effective_commission_pct * (exit_price / entry_price)
            cost_pct = sell_commission_pct + sell_tax_pct + buyback_commission_pct

        net_pnl_pct = gross_pnl_pct - cost_pct
        result = "WIN" if net_pnl_pct > 0 else "LOSS"
        if abs(net_pnl_pct) < 0.03:
            result = "FLAT"

        hold_bars = max(0, exit_index - entry_index)

        return {
            "exit_price": exit_price,
            "exit_reason": exit_reason,
            "exit_index": exit_index,
            "gross_pnl_pct": gross_pnl_pct,
            "cost_pct": cost_pct,
            "pnl_pct": net_pnl_pct,
            "result": result,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "stop_loss_pct": stop_loss_pct,
            "take_profit_pct": take_profit_pct,
            "commission_rate_pct": commission_rate_pct,
            "commission_discount": commission_discount,
            "effective_commission_pct": effective_commission_pct,
            "tax_rate_pct": tax_rate_pct,
            "hold_bars": hold_bars,
            "max_hold_bars": max_hold_bars,
            "best_favorable_pct": best_favorable_pct,
        }

    @staticmethod
    def _summarize(trades):
        total = len(trades)
        wins = len([t for t in trades if t["result"] == "WIN"])
        losses = len([t for t in trades if t["result"] == "LOSS"])
        flats = len([t for t in trades if t["result"] == "FLAT"])
        win_rate = wins / total * 100 if total else 0

        total_pnl = sum(t["pnl_pct"] for t in trades)
        avg_pnl = total_pnl / total if total else 0
        gross_total_pnl = sum(t.get("gross_pnl_pct", t.get("pnl_pct", 0)) for t in trades)
        total_cost_pct = sum(t.get("cost_pct", 0) for t in trades)

        gross_profit = sum(t["pnl_pct"] for t in trades if t["pnl_pct"] > 0)
        gross_loss = abs(sum(t["pnl_pct"] for t in trades if t["pnl_pct"] < 0))

        if gross_loss > 0:
            profit_factor = gross_profit / gross_loss
        elif gross_profit > 0:
            profit_factor = 999
        else:
            profit_factor = 0

        equity = 0
        peak = 0
        max_drawdown = 0
        max_consecutive_loss = 0
        current_loss_streak = 0

        for t in trades:
            equity += t["pnl_pct"]
            peak = max(peak, equity)
            drawdown = peak - equity
            max_drawdown = max(max_drawdown, drawdown)

            if t["result"] == "LOSS":
                current_loss_streak += 1
                max_consecutive_loss = max(max_consecutive_loss, current_loss_streak)
            else:
                current_loss_streak = 0

        buy_trades = [t for t in trades if t["action"] == "BUY"]
        sell_trades = [t for t in trades if t["action"] == "SELL"]
        buy_wins = len([t for t in buy_trades if t["result"] == "WIN"])
        sell_wins = len([t for t in sell_trades if t["result"] == "WIN"])
        buy_win_rate = buy_wins / len(buy_trades) * 100 if buy_trades else 0
        sell_win_rate = sell_wins / len(sell_trades) * 100 if sell_trades else 0

        predicted_ev_values = [t.get("predicted_expected_value") for t in trades if t.get("predicted_expected_value") is not None]
        avg_predicted_ev = sum(predicted_ev_values) / len(predicted_ev_values) if predicted_ev_values else 0

        return {
            "total": total,
            "wins": wins,
            "losses": losses,
            "flats": flats,
            "win_rate": win_rate,
            "buy_count": len(buy_trades),
            "sell_count": len(sell_trades),
            "buy_win_rate": buy_win_rate,
            "sell_win_rate": sell_win_rate,
            "total_pnl": total_pnl,
            "avg_pnl": avg_pnl,
            "gross_total_pnl": gross_total_pnl,
            "total_cost_pct": total_cost_pct,
            "net_total_pnl": total_pnl,
            "profit_factor": profit_factor,
            "max_drawdown": max_drawdown,
            "max_consecutive_loss": max_consecutive_loss,
            "avg_predicted_ev": avg_predicted_ev,
        }

    @staticmethod
    def _get_prediction_value(decision, path, default=None):
        cur = decision
        for key in path:
            if not isinstance(cur, dict) or key not in cur:
                return default
            cur = cur[key]
        return cur

    @staticmethod
    def _flatten_day_items(day_items):
        out = []
        for item in day_items:
            out.extend(item.get("candles", []))
        return out

    @staticmethod
    def _build_model_package_from_candles(
        candles,
        symbol,
        timeframe,
        default_stop_pct,
        default_take_pct,
        max_hold_bars,
        estimated_cost_pct,
    ):
        if StockModelCache is None:
            return None, "StockModelCache 未載入，無法建立模型。"

        if not candles:
            return None, "訓練資料不足，無法建立模型。"

        try:
            model_package = StockModelCache.build_model_package(
                kline_df=BacktestEngine._candles_to_dataframe(candles),
                symbol=symbol,
                timeframe=timeframe,
                stop_pct=default_stop_pct,
                take_pct=default_take_pct,
                max_hold_bars=max_hold_bars,
                cost_pct=estimated_cost_pct,
            )

            label_rows = int(model_package.get("label_rows", 0) or 0)

            if label_rows <= 0:
                return None, "模型標籤數為 0，無法使用模型判斷。"

            return model_package, (
                f"模型區間 {model_package.get('start_date')} ~ {model_package.get('end_date')}，"
                f"標籤 {label_rows} 筆。"
            )

        except Exception as e:
            return None, f"模型建立失敗：{type(e).__name__}"


    @staticmethod
    def run(
        api_key,
        symbol,
        timeframe="1",
        score_threshold=65,
        require_resonance=False,
        avoid_open_minutes=15,
        cooldown_bars=5,
        max_hold_bars=50,
        day_scope="last_open_day",
        default_stop_pct=0.7,
        default_take_pct=1.8,
        commission_rate_pct=0.1425,
        commission_discount=1.0,
        tax_rate_pct=0.15,
        model_mode="realtime_structure",
        scan_step_bars=1,
        max_runtime_seconds=120,
        pro_filters_enabled=True,
        max_trades_per_day=3,
        loss_cooldown_bars=30,
        stop_after_losses=2,
        progress_callback=None,
    ):
        """
        model_mode:
        - realtime_structure：即時結構 AI，不訓練、不用歷史標籤，只看當下盤中量價。
        - walk_forward：歷史校準模式。測某一天時，只用該日以前「全部可用歷史資料」建立模型。
        - same_period：Debug 模式。用同一段資料建立模型再回測，會有資料洩漏。
        - classic：不使用近 30 日模型，只跑一般 AI 備援。
        """

        start_time = time.time()
        scan_step_bars = max(1, BacktestEngine._safe_int(scan_step_bars, 1))
        max_runtime_seconds = max(15, BacktestEngine._safe_int(max_runtime_seconds, 55))

        def _progress(message, percent=None):
            if progress_callback is None:
                return
            try:
                progress_callback(message, percent)
            except Exception:
                pass

        _progress("正在抓 Fugle 歷史 K 線...", 2)

        candles = BacktestEngine.fetch_historical_candles(
            api_key=api_key,
            symbol=symbol,
            timeframe=timeframe,
        )

        if not candles:
            return {"ok": False, "message": "沒有取得歷史 K 線資料。", "summary": {}, "trades": []}

        days = BacktestEngine._group_by_day(candles)
        selected_days = BacktestEngine._select_days(days=days, day_scope=day_scope)

        valid_days = []
        for day in sorted(days.keys()):
            day_candles = days[day]
            if len(day_candles) >= 40:
                valid_days.append({"date": day, "candles": day_candles})

        valid_day_index = {item["date"]: idx for idx, item in enumerate(valid_days)}

        if not selected_days:
            return {
                "ok": False,
                "message": "沒有找到足夠 K 線的開市日。",
                "summary": {},
                "trades": [],
                "candles": len(candles),
                "days": len(days),
            }

        try:
            timeframe_int = max(1, int(timeframe))
        except Exception:
            timeframe_int = 1

        avoid_bars = max(0, math.ceil(avoid_open_minutes / timeframe_int))
        # Walk-forward 真實模式不再提供「訓練天數」參數。
        # 測某一天時，模型只使用該日以前所有可用歷史交易日；這比較接近真實盤。
        max_trades_per_day = max(1, BacktestEngine._safe_int(max_trades_per_day, 2))
        loss_cooldown_bars = max(0, BacktestEngine._safe_int(loss_cooldown_bars, 30))
        stop_after_losses = max(1, BacktestEngine._safe_int(stop_after_losses, 2))
        # 嚴格移除「每日候選模式」。
        # 回測只能根據當下已達正期望的訊號進場，不允許為了每天有交易而放寬成候選單。

        effective_commission_pct = commission_rate_pct * commission_discount
        estimated_cost_pct = effective_commission_pct + effective_commission_pct + tax_rate_pct

        trades = []
        skipped_days = []
        day_model_messages = []

        shared_model_package = None
        shared_model_message = ""
        prebuilt_enriched_df = None
        prebuilt_labels_df = None

        _progress(f"已取得 {len(candles)} 根 K 線，準備回測 {len(selected_days)} 個交易日...", 8)

        if model_mode in ["walk_forward", "same_period"]:
            _progress("正在建立全區間標籤快取，之後每天只切過去資料，不重複重建模型...", 10)
            try:
                prebuilt_enriched_df, prebuilt_labels_df = IntradayLabelEngine.build_labels(
                    kline_df=BacktestEngine._candles_to_dataframe(candles),
                    stop_pct=default_stop_pct,
                    take_pct=default_take_pct,
                    max_hold_bars=max_hold_bars,
                    cost_pct=estimated_cost_pct,
                    start_minute=15,
                    end_minute=250,
                )
            except Exception as e:
                prebuilt_enriched_df = None
                prebuilt_labels_df = None
                skipped_days.append({"date": "PREBUILD", "reason": f"標籤快取建立失敗：{type(e).__name__}"})

        if model_mode == "same_period":
            _progress("正在建立同區間 Debug 模型...", 12)
            if prebuilt_enriched_df is not None and prebuilt_labels_df is not None and not prebuilt_labels_df.empty:
                shared_model_package = StockModelCache.build_model_package_from_prebuilt(
                    enriched_df=prebuilt_enriched_df,
                    labels_df=prebuilt_labels_df,
                    symbol=symbol,
                    timeframe=timeframe,
                    stop_pct=default_stop_pct,
                    take_pct=default_take_pct,
                    max_hold_bars=max_hold_bars,
                    cost_pct=estimated_cost_pct,
                )
                shared_model_message = f"同區間模型（有資料洩漏，只能 Debug）：標籤 {shared_model_package.get('label_rows', 0)} 筆。"
            else:
                shared_model_package, shared_model_message = BacktestEngine._build_model_package_from_candles(
                    candles=candles,
                    symbol=symbol,
                    timeframe=timeframe,
                    default_stop_pct=default_stop_pct,
                    default_take_pct=default_take_pct,
                    max_hold_bars=max_hold_bars,
                    estimated_cost_pct=estimated_cost_pct,
                )
                shared_model_message = "同區間模型（有資料洩漏，只能 Debug）：" + shared_model_message

        elif model_mode == "classic":
            shared_model_message = "一般 AI 模式：未使用近 30 日相似 K 線模型。"

        elif model_mode == "realtime_structure":
            shared_model_message = (
                "即時結構 AI：不訓練、不使用事後結果、不設定訓練天數；"
                "每一根 K 只用當下以前的 ORB / VWAP / Tape Flow / 五檔 / 盤勢 / 動態風控判斷；"
                "每日最多交易=當天即時達標訊號；第二筆自動提高門檻，不回頭挑最佳點。"
                f"｜每日最多 {max_trades_per_day} 筆"
            )

        else:
            model_mode = "realtime_structure"
            shared_model_message = (
                "即時結構 AI：不訓練、不使用事後結果、不設定訓練天數；"
                "每一根 K 只用當下以前的 ORB / VWAP / Tape Flow / 五檔 / 盤勢 / 動態風控判斷；"
                "每日最多交易=當天即時達標訊號；第二筆自動提高門檻，不回頭挑最佳點。"
                f"｜每日最多 {max_trades_per_day} 筆"
            )

        for day_pos, day_item in enumerate(selected_days, start=1):
            if time.time() - start_time > max_runtime_seconds:
                skipped_days.append({"date": "TIME_LIMIT", "reason": f"超過 {max_runtime_seconds} 秒，已提前結束並保留已完成結果"})
                break

            day = day_item["date"]
            day_candles = day_item["candles"]

            if len(day_candles) < 40:
                continue

            base_percent = 10 + int((day_pos - 1) / max(len(selected_days), 1) * 85)
            _progress(f"即時結構回測中：{day}（{day_pos}/{len(selected_days)}）", base_percent)

            model_package = None
            model_message = ""
            model_train_start = ""
            model_train_end = ""
            model_train_days = 0

            if model_mode == "realtime_structure":
                model_package = None
                model_message = shared_model_message

            elif model_mode == "same_period":
                model_package = shared_model_package
                model_message = shared_model_message
                if model_package:
                    model_train_start = model_package.get("start_date", "")
                    model_train_end = model_package.get("end_date", "")
                    model_train_days = int(model_package.get("trading_days", 0) or 0)

            elif model_mode == "classic":
                model_package = None
                model_message = shared_model_message

            else:
                idx = valid_day_index.get(day, -1)

                if idx <= 0:
                    skipped_days.append({"date": day, "reason": "沒有更早交易日可建模"})
                    continue

                # Expanding walk-forward：只使用測試日前所有歷史資料。
                # 不再讓使用者設定「訓練天數」，避免變成調參數追績效。
                train_day_items = valid_days[:idx]
                model_train_days = len(train_day_items)

                if model_train_days < 3:
                    skipped_days.append({
                        "date": day,
                        "reason": f"可用歷史資料不足：{model_train_days} 日",
                    })
                    continue

                train_candles = BacktestEngine._flatten_day_items(train_day_items)
                model_train_start = train_day_items[0]["date"] if train_day_items else ""
                model_train_end = train_day_items[-1]["date"] if train_day_items else ""
                _progress(f"{day}：使用該日前全部 {model_train_days} 日歷史資料建模...", min(base_percent + 2, 95))

                if prebuilt_enriched_df is not None and prebuilt_labels_df is not None and not prebuilt_labels_df.empty:
                    train_dates = [x["date"] for x in train_day_items]
                    train_enriched = prebuilt_enriched_df[prebuilt_enriched_df["trade_date"].isin(train_dates)].copy()
                    train_labels = prebuilt_labels_df[prebuilt_labels_df["trade_date"].isin(train_dates)].copy()
                    if train_labels.empty:
                        model_package = None
                        model_message = "訓練標籤為 0，無法使用模型。"
                    else:
                        model_package = StockModelCache.build_model_package_from_prebuilt(
                            enriched_df=train_enriched,
                            labels_df=train_labels,
                            symbol=symbol,
                            timeframe=timeframe,
                            stop_pct=default_stop_pct,
                            take_pct=default_take_pct,
                            max_hold_bars=max_hold_bars,
                            cost_pct=estimated_cost_pct,
                        )
                        model_message = f"快取模型區間 {model_train_start} ~ {model_train_end}，標籤 {model_package.get('label_rows', 0)} 筆。"
                else:
                    model_package, model_message = BacktestEngine._build_model_package_from_candles(
                        candles=train_candles,
                        symbol=symbol,
                        timeframe=timeframe,
                        default_stop_pct=default_stop_pct,
                        default_take_pct=default_take_pct,
                        max_hold_bars=max_hold_bars,
                        estimated_cost_pct=estimated_cost_pct,
                    )

                day_model_messages.append(f"{day}: {model_message}")

                if model_package is None:
                    skipped_days.append({"date": day, "reason": model_message})
                    continue

            day_opens, day_highs, day_lows, day_prices, day_volumes, day_vwaps, day_times = BacktestEngine._build_ohlcv_series(day_candles)
            i = max(20, avoid_bars)
            day_trade_count = 0
            day_loss_streak = 0
            next_allowed_index = i

            while i < len(day_candles) - 2:
                if day_trade_count >= max_trades_per_day:
                    skipped_days.append({"date": day, "reason": f"已達每日最多 {max_trades_per_day} 筆"})
                    break

                if i < next_allowed_index:
                    i = next_allowed_index
                    continue
                if time.time() - start_time > max_runtime_seconds:
                    skipped_days.append({"date": day, "reason": f"超過 {max_runtime_seconds} 秒，提前停止"})
                    break

                # 只傳到目前 K 為止，不偷看未來。
                decision = BacktestEngine._make_decision_from_series(
                    prices=day_prices[: i + 1],
                    volumes=day_volumes[: i + 1],
                    vwaps=day_vwaps[: i + 1],
                    times=day_times[: i + 1],
                    model_package=model_package,
                    use_multi_period=False,
                    require_resonance=require_resonance,
                    use_realtime_signal=(model_mode == "realtime_structure"),
                    opens=day_opens[: i + 1],
                    highs=day_highs[: i + 1],
                    lows=day_lows[: i + 1],
                    stop_pct=default_stop_pct,
                    take_pct=default_take_pct,
                    cost_pct=estimated_cost_pct,
                )

                if not decision:
                    i += scan_step_bars
                    continue

                action = decision.get("action", "WAIT")
                score = BacktestEngine._safe_int(decision.get("score", 0))

                multi_period = decision.get("multi_period", {}) or {}
                resonance = multi_period.get("resonance", "WAIT")
                multi_status = decision.get("multi_period_status", "盤整觀望")

                if action not in ["BUY", "SELL"]:
                    i += scan_step_bars
                    continue

                effective_score_threshold = score_threshold

                # 第二筆交易不應該和第一筆用同一門檻。
                # 當天已經出現一次有效訊號後，第二次通常是盤整、追價或反彈失敗區，
                # 因此自動提高門檻；這不是每日候選，而是即時風控。
                if day_trade_count >= 1:
                    effective_score_threshold += 8

                if score < effective_score_threshold:
                    i += scan_step_bars
                    continue

                if require_resonance:
                    if action == "BUY" and resonance not in ["BULL", "BULL_STRONG"]:
                        i += 1
                        continue
                    if action == "SELL" and resonance not in ["BEAR", "BEAR_STRONG"]:
                        i += 1
                        continue

                entry_index = i + 1
                if entry_index >= len(day_candles):
                    break

                entry_candle = day_candles[entry_index]
                entry_price = BacktestEngine._safe_float(entry_candle["open"])
                if entry_price <= 0:
                    entry_price = BacktestEngine._safe_float(entry_candle["close"])

                exit_data = BacktestEngine._simulate_exit(
                    action=action,
                    entry_price=entry_price,
                    entry_index=entry_index,
                    day_candles=day_candles,
                    decision=decision,
                    max_hold_bars=max_hold_bars,
                    default_stop_pct=default_stop_pct,
                    default_take_pct=default_take_pct,
                    commission_rate_pct=commission_rate_pct,
                    commission_discount=commission_discount,
                    tax_rate_pct=tax_rate_pct,
                )

                exit_index = exit_data["exit_index"]
                exit_candle = day_candles[exit_index]
                swing_prediction = decision.get("swing_prediction", {}) or {}
                chosen = swing_prediction.get("chosen", {}) or {}
                buy_pred = swing_prediction.get("buy", {}) or {}
                sell_pred = swing_prediction.get("sell", {}) or {}
                feature_pred = swing_prediction.get("feature", {}) or {}
                streak_pred = swing_prediction.get("streak_volume", {}) or {}

                trades.append(
                    {
                        "date": day,
                        "model_mode": model_mode,
                        "model_train_start": model_train_start,
                        "model_train_end": model_train_end,
                        "model_train_days": model_train_days,
                        "model_label_rows": model_package.get("label_rows", 0) if model_package else 0,
                        "action": action,
                        "score": score,
                        "multi_status": multi_status,
                        "resonance": resonance,
                        "entry_time": entry_candle["time"].strftime("%H:%M"),
                        "entry_price": round(entry_price, 2),
                        "stop_loss": round(exit_data["stop_loss"], 2),
                        "take_profit": round(exit_data["take_profit"], 2),
                        "stop_loss_pct": round(exit_data["stop_loss_pct"], 2),
                        "take_profit_pct": round(exit_data["take_profit_pct"], 2),
                        "exit_time": exit_candle["time"].strftime("%H:%M"),
                        "exit_price": round(exit_data["exit_price"], 2),
                        "exit_reason": exit_data["exit_reason"],
                        "hold_bars": exit_data["hold_bars"],
                        "max_hold_bars": exit_data["max_hold_bars"],
                        "gross_pnl_pct": round(exit_data["gross_pnl_pct"], 3),
                        "cost_pct": round(exit_data["cost_pct"], 3),
                        "pnl_pct": round(exit_data["pnl_pct"], 3),
                        "commission_rate_pct": round(exit_data["commission_rate_pct"], 4),
                        "commission_discount": round(exit_data["commission_discount"], 2),
                        "effective_commission_pct": round(exit_data["effective_commission_pct"], 4),
                        "tax_rate_pct": round(exit_data["tax_rate_pct"], 3),
                        "predicted_expected_value": chosen.get("expected_value"),
                        "predicted_win_rate": chosen.get("win_rate"),
                        "required_win_rate": swing_prediction.get("required_win_rate"),
                        "estimated_mfe_pct": decision.get("estimated_mfe_pct", chosen.get("estimated_mfe_pct")),
                        "estimated_mae_pct": decision.get("estimated_mae_pct", chosen.get("estimated_mae_pct")),
                        "mfe_mae_ratio": decision.get("mfe_mae_ratio", chosen.get("mfe_mae_ratio")),
                        "ev_after_quality": decision.get("ev_after_quality", chosen.get("ev_after_quality")),
                        "quality_adjustment": chosen.get("quality_adjustment"),
                        "quality_fail_reasons": " | ".join(chosen.get("quality_fail_reasons", [])[:5]) if isinstance(chosen.get("quality_fail_reasons"), list) else chosen.get("quality_fail_reasons"),
                        "quality_reasons": " | ".join(chosen.get("quality_reasons", [])[:5]) if isinstance(chosen.get("quality_reasons"), list) else chosen.get("quality_reasons"),
                        "best_favorable_pct": round(exit_data.get("best_favorable_pct", 0), 3),
                        "predicted_sample_count": chosen.get("sample_count"),
                        "buy_expected_value": buy_pred.get("expected_value"),
                        "sell_expected_value": sell_pred.get("expected_value"),
                        "buy_win_rate": buy_pred.get("win_rate"),
                        "sell_win_rate": sell_pred.get("win_rate"),
                        "risk_level": decision.get("risk_level"),
                        "setup_type": chosen.get("setup_type"),
                        "raw_win_rate": chosen.get("raw_win_rate"),
                        "calibrated_win_rate": chosen.get("calibrated_win_rate", chosen.get("win_rate")),
                        "raw_expected_value": chosen.get("raw_expected_value"),
                        "calibrated_expected_value": chosen.get("calibrated_expected_value", chosen.get("expected_value")),
                        "filter_penalty": chosen.get("filter_penalty"),
                        "professional_pass": chosen.get("professional_pass"),
                        "professional_filters": " | ".join(chosen.get("professional_filters", [])[:5]) if isinstance(chosen.get("professional_filters"), list) else chosen.get("professional_filters"),
                        "hard_fail_reasons": " | ".join(chosen.get("hard_fail_reasons", [])[:5]) if isinstance(chosen.get("hard_fail_reasons"), list) else chosen.get("hard_fail_reasons"),
                        "tape_buy_pressure": (swing_prediction.get("tape_flow", {}) or {}).get("buy_pressure"),
                        "tape_sell_pressure": (swing_prediction.get("tape_flow", {}) or {}).get("sell_pressure"),
                        "orderbook_imbalance": (swing_prediction.get("orderbook_flow", {}) or {}).get("imbalance"),
                        "market_regime": (swing_prediction.get("market_context", {}) or {}).get("regime"),
                        "market_quality": (swing_prediction.get("market_context", {}) or {}).get("quality"),
                        "adaptive_stop_pct": decision.get("adaptive_stop_pct"),
                        "adaptive_take_pct": decision.get("adaptive_take_pct"),
                        "clock_minute": feature_pred.get("clock_minute"),
                        "orb_ready": feature_pred.get("orb_ready"),
                        "missing_open_data": feature_pred.get("missing_open_data"),
                        "vwap_gap": feature_pred.get("vwap_gap"),
                        "close_location": feature_pred.get("close_location"),
                        "volume_ratio_5": feature_pred.get("volume_ratio_5"),
                        "volume_acceleration": feature_pred.get("volume_acceleration"),
                        "buy_streak_count": streak_pred.get("buy_streak_count"),
                        "sell_streak_count": streak_pred.get("sell_streak_count"),
                        "buy_streak_volume": streak_pred.get("buy_streak_volume"),
                        "sell_streak_volume": streak_pred.get("sell_streak_volume"),
                        "streak_volume_ratio": streak_pred.get("streak_volume_ratio"),
                        "streak_follow_through": streak_pred.get("streak_follow_through"),
                        "volume_exhaustion_risk": streak_pred.get("volume_exhaustion_risk"),
                        "absorption_risk": streak_pred.get("absorption_risk"),
                        "streak_reasons": " | ".join(streak_pred.get("reasons", [])[:5]) if isinstance(streak_pred.get("reasons"), list) else streak_pred.get("reasons"),
                        "result": exit_data["result"],
                    }
                )

                day_trade_count += 1

                if exit_data["result"] == "LOSS":
                    day_loss_streak += 1
                    i = exit_index + max(cooldown_bars, loss_cooldown_bars)
                    if day_loss_streak >= stop_after_losses:
                        skipped_days.append({"date": day, "reason": f"連續虧損 {day_loss_streak} 筆，當日停止交易"})
                        break
                else:
                    day_loss_streak = 0
                    i = exit_index + cooldown_bars

        summary = BacktestEngine._summarize(trades)
        summary["skipped_days"] = len(skipped_days)
        summary["model_mode"] = model_mode
        selected_day_names = [d["date"] for d in selected_days]

        if model_mode == "same_period":
            leak_warning = "同區間模型有資料洩漏風險，不代表真實 AI 能力。"
        elif model_mode == "walk_forward":
            leak_warning = "Walk-forward：測試日只使用該日前所有歷史資料建模，不偷看未來。"
        elif model_mode == "realtime_structure":
            leak_warning = "專業即時結構 AI：只使用當下以前的盤中資料，不訓練、不偷看未來；每日最多交易代表當天第一個達標訊號，不是事後候選。"
        else:
            leak_warning = "一般 AI：未使用相似 K 線成本模型。"

        elapsed_seconds = round(time.time() - start_time, 2)
        _progress(f"回測完成，用時 {elapsed_seconds} 秒", 100)

        message = f"回測完成｜用時 {elapsed_seconds} 秒｜{leak_warning}｜{shared_model_message}"
        if not trades:
            message = f"回測完成，但沒有符合正期望條件的交易；這代表目前 AI 精準度或濾網仍不足，不會用事後結果或候選單硬湊交易。｜{leak_warning}｜{shared_model_message}"

        return {
            "ok": True,
            "message": message,
            "symbol": symbol,
            "timeframe": timeframe,
            "candles": len(candles),
            "all_days": len(days),
            "days": len(selected_days),
            "selected_days": selected_day_names,
            "model_mode": model_mode,
            "history_mode": "realtime_structure" if model_mode == "realtime_structure" else "expanding_past_only",
            "scan_step_bars": scan_step_bars,
            "max_trades_per_day": max_trades_per_day,
            "loss_cooldown_bars": loss_cooldown_bars,
            "stop_after_losses": stop_after_losses,
            "pro_filters_enabled": pro_filters_enabled,
            "elapsed_seconds": elapsed_seconds,
            "leak_warning": leak_warning,
            "model_message": shared_model_message,
            "skipped_days": skipped_days,
            "day_model_messages": day_model_messages[-8:],
            "model_label_rows": shared_model_package.get("label_rows", 0) if shared_model_package else 0,
            "summary": summary,
            "trades": trades,
        }
