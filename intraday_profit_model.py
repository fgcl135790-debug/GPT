import pandas as pd
import numpy as np


class IntradayProfitModel:
    """
    成本感知 + 專業濾網的相似 K 線當沖模型。

    這版不再只看原始勝率，而是加入：
    1. 扣成本後期望報酬 expected_value
    2. 校準後勝率 calibrated_win_rate
    3. ORB / VWAP / 量能 / 時段 / 假突破濾網
    4. 樣本數不足與午盤低量的保守折扣
    """

    FEATURE_COLS = [
        "vwap_gap", "vwap_abs_gap", "ema_gap", "rsi", "macd_hist",
        "slope_3", "slope_5", "slope_10", "slope_20",
        "volume_ratio", "volume_ratio_5", "volume_ratio_20", "volume_acceleration",
        "distance_to_high_30", "distance_to_low_30", "distance_to_high_60", "distance_to_low_60",
        "open_gap", "day_range_pct",
        "orb_high_gap", "orb_low_gap", "orb_range_pct",
        "candle_range_pct", "close_location", "upper_wick_pct", "lower_wick_pct",
    ]

    def __init__(self, labels_df):
        self.labels = labels_df.copy() if labels_df is not None else pd.DataFrame()
        if not self.labels.empty:
            self.labels = self.labels.replace([np.inf, -np.inf], np.nan).fillna(0)
            if "trade_date" in self.labels.columns:
                self.training_days = int(self.labels["trade_date"].nunique())
            else:
                self.training_days = 0
        else:
            self.training_days = 0
        self.feature_stats = self._build_feature_stats()

    @staticmethod
    def _safe_float(value, default=0.0):
        try:
            if value is None or pd.isna(value):
                return default
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
    def _clamp(value, low, high):
        return max(low, min(high, value))

    def _build_feature_stats(self):
        stats = {}
        if self.labels.empty:
            return stats
        for col in self.FEATURE_COLS:
            if col not in self.labels.columns:
                continue
            std = float(self.labels[col].std())
            if std <= 0 or np.isnan(std):
                std = 1.0
            stats[col] = {"mean": float(self.labels[col].mean()), "std": std}
        return stats

    @staticmethod
    def required_win_rate_pct(stop_pct=0.7, take_pct=1.8, cost_pct=0.435, safety_margin=5.0):
        stop_pct = IntradayProfitModel._safe_float(stop_pct, 0.7)
        take_pct = IntradayProfitModel._safe_float(take_pct, 1.8)
        cost_pct = IntradayProfitModel._safe_float(cost_pct, 0.435)
        safety_margin = IntradayProfitModel._safe_float(safety_margin, 5.0)
        win_net = take_pct - cost_pct
        loss_net = stop_pct + cost_pct
        if win_net <= 0:
            return 99.0
        breakeven = loss_net / max(win_net + loss_net, 0.000001) * 100
        return round(min(95.0, breakeven + safety_margin), 2)

    def _distance_score(self, df, feature):
        dist = pd.Series(0.0, index=df.index)
        weights = {
            "vwap_gap": 1.65,
            "vwap_abs_gap": 1.20,
            "ema_gap": 1.05,
            "rsi": 0.70,
            "macd_hist": 1.05,
            "slope_3": 1.65,
            "slope_5": 1.45,
            "slope_10": 1.35,
            "slope_20": 0.85,
            "volume_ratio": 0.90,
            "volume_ratio_5": 1.25,
            "volume_ratio_20": 1.00,
            "volume_acceleration": 1.25,
            "distance_to_high_30": 1.15,
            "distance_to_low_30": 1.15,
            "distance_to_high_60": 0.75,
            "distance_to_low_60": 0.75,
            "open_gap": 0.80,
            "day_range_pct": 0.70,
            "orb_high_gap": 1.65,
            "orb_low_gap": 1.65,
            "orb_range_pct": 0.75,
            "candle_range_pct": 0.55,
            "close_location": 0.75,
            "upper_wick_pct": 0.55,
            "lower_wick_pct": 0.55,
        }
        for col in self.FEATURE_COLS:
            if col not in df.columns:
                continue
            stat = self.feature_stats.get(col, {"std": 1.0})
            std = max(stat.get("std", 1.0), 0.000001)
            target = self._safe_float(feature.get(col), 0.0)
            dist += ((df[col] - target).abs() / std) * weights.get(col, 1.0)
        return dist

    def _summarize(self, sample, action, feature, level):
        if sample.empty:
            return {
                "action": action,
                "level": level,
                "sample_count": 0,
                "win_rate": 0.0,
                "raw_win_rate": 0.0,
                "loss_rate": 0.0,
                "time_rate": 0.0,
                "avg_pnl_pct": -999.0,
                "median_pnl_pct": -999.0,
                "expected_value": -999.0,
                "raw_expected_value": -999.0,
                "calibrated_win_rate": 0.0,
                "calibrated_expected_value": -999.0,
                "profit_factor": 0.0,
                "reason": "沒有相似樣本",
            }

        wins = sample[sample["pnl_pct"] > 0]
        losses = sample[sample["pnl_pct"] <= 0]
        time_exits = sample[sample.get("exit_reason", "") == "時間出場"] if "exit_reason" in sample.columns else pd.DataFrame()

        win_rate = len(wins) / len(sample) * 100
        loss_rate = len(losses) / len(sample) * 100
        time_rate = len(time_exits) / len(sample) * 100 if len(sample) else 0
        avg_pnl = float(sample["pnl_pct"].mean())
        median_pnl = float(sample["pnl_pct"].median())
        gross_win = float(wins["pnl_pct"].sum()) if not wins.empty else 0.0
        gross_loss = abs(float(losses["pnl_pct"].sum())) if not losses.empty else 0.0
        profit_factor = 99.0 if gross_loss <= 0 and gross_win > 0 else (gross_win / gross_loss if gross_loss > 0 else 0.0)

        reason = f"{level} 相似樣本 {len(sample)} 筆，原始勝率 {win_rate:.1f}%，扣成本均值 {avg_pnl:.3f}%"
        return {
            "action": action,
            "level": level,
            "sample_count": int(len(sample)),
            "win_rate": round(win_rate, 2),
            "raw_win_rate": round(win_rate, 2),
            "loss_rate": round(loss_rate, 2),
            "time_rate": round(time_rate, 2),
            "avg_pnl_pct": round(avg_pnl, 3),
            "median_pnl_pct": round(median_pnl, 3),
            "expected_value": round(avg_pnl, 3),
            "raw_expected_value": round(avg_pnl, 3),
            "calibrated_win_rate": round(win_rate, 2),
            "calibrated_expected_value": round(avg_pnl, 3),
            "profit_factor": round(profit_factor, 2),
            "best_time_bucket": str(feature.get("time_bucket", "")),
            "reason": reason,
        }

    def predict_action(self, feature, action, top_n=120):
        if self.labels.empty:
            return self._summarize(pd.DataFrame(), action, feature, "EMPTY")
        df = self.labels[self.labels["action"] == action].copy()
        if df.empty:
            return self._summarize(pd.DataFrame(), action, feature, "NO_ACTION")

        time_bucket = feature.get("time_bucket")
        vwap_zone = feature.get("vwap_zone")
        slope_zone = feature.get("slope_zone")
        orb_zone = feature.get("orb_zone")

        strict = df[
            (df["time_bucket"] == time_bucket)
            & (df["vwap_zone"] == vwap_zone)
            & (df["slope_zone"] == slope_zone)
            & (df.get("orb_zone", "") == orb_zone)
        ].copy()
        if len(strict) >= 22:
            candidate, level = strict, "STRICT"
        else:
            medium = df[
                (df["time_bucket"] == time_bucket)
                & (df["slope_zone"] == slope_zone)
            ].copy()
            if len(medium) >= 35:
                candidate, level = medium, "MEDIUM"
            else:
                loose = df[df["time_bucket"] == time_bucket].copy()
                if len(loose) >= 50:
                    candidate, level = loose, "TIME_ONLY"
                else:
                    candidate, level = df.copy(), "ALL"

        if candidate.empty:
            return self._summarize(pd.DataFrame(), action, feature, level)
        candidate["distance"] = self._distance_score(candidate, feature)
        sample = candidate.sort_values("distance").head(top_n).copy()
        return self._summarize(sample, action, feature, level)

    def _professional_calibration(self, result, feature, action, required_win_rate, min_expected_value):
        result = dict(result)
        minute = self._safe_int(feature.get("minute_index"), 0)
        vwap_gap = self._safe_float(feature.get("vwap_gap"), 0)
        vwap_abs_gap = abs(vwap_gap)
        slope3 = self._safe_float(feature.get("slope_3"), 0)
        slope10 = self._safe_float(feature.get("slope_10"), 0)
        volume5 = self._safe_float(feature.get("volume_ratio_5"), 1.0)
        volume_acc = self._safe_float(feature.get("volume_acceleration"), 1.0)
        orb_high_gap = self._safe_float(feature.get("orb_high_gap"), 0)
        orb_low_gap = self._safe_float(feature.get("orb_low_gap"), 0)
        close_location = self._safe_float(feature.get("close_location"), 0.5)
        upper_wick = self._safe_float(feature.get("upper_wick_pct"), 0)
        lower_wick = self._safe_float(feature.get("lower_wick_pct"), 0)
        dist_high30 = self._safe_float(feature.get("distance_to_high_30"), 0)
        dist_low30 = self._safe_float(feature.get("distance_to_low_30"), 0)

        filters = []
        blocks = []
        penalty = 0.0
        setup_type = "NONE"

        # 樣本與回測可信度校準
        sample_count = self._safe_int(result.get("sample_count"), 0)
        level = result.get("level", "ALL")
        if sample_count < 25:
            penalty += 7
            filters.append("樣本少於 25 筆，勝率折扣 7%")
        elif sample_count < 50:
            penalty += 3
            filters.append("樣本少於 50 筆，勝率折扣 3%")
        # 不再使用「訓練天數」當作交易訊號懲罰。
        # 真實盤中不會因為使用者設定 N 天而改變當下量價結構；
        # 可信度改由樣本數、相似層級、EV、VWAP/ORB/量能濾網校準。
        if level in ["ALL", "TIME_ONLY"]:
            penalty += 3 if level == "ALL" else 2
            filters.append(f"相似層級 {level}，不是嚴格相似，保守折扣")

        # 時段濾網：午盤低量不輕易開新倉
        if minute >= 150:
            penalty += 5
            filters.append("11:30 後新倉，低量與假突破風險提高")
        if minute >= 210:
            penalty += 7
            filters.append("12:30 後新倉，停利空間通常不足，提高門檻")

        # 方向與 ORB / VWAP 對齊
        if action == "BUY":
            orb_break = orb_high_gap >= -0.08
            vwap_ok = vwap_gap >= -0.05
            momentum_ok = slope3 >= -0.10 and slope10 >= -0.25
            if orb_high_gap >= -0.05 and vwap_gap >= -0.03 and volume5 >= 0.65:
                setup_type = "ORB突破做多"
                filters.append("多方 ORB / VWAP 同向")
            elif vwap_gap >= 0.15 and momentum_ok:
                setup_type = "VWAP上方趨勢做多"
                filters.append("價格站上 VWAP 且短線動能未轉弱")
            elif vwap_gap < -0.7 and slope3 > 0.25 and volume_acc >= 0.9:
                setup_type = "急跌後反彈做多"
                filters.append("VWAP 下方反彈型，多看反彈不追高")
            else:
                penalty += 5
                filters.append("做多未完全通過 ORB / VWAP / 動能主要濾網，改為降權觀察")

            if vwap_gap > 1.5 and dist_high30 < 0.20:
                penalty += 12
                filters.append("價格離 VWAP 太遠且靠近 30K 高點，追高風險")
            if close_location < 0.35 and upper_wick > lower_wick:
                penalty += 5
                filters.append("K 棒收盤位置偏弱，上影線壓力較大")
            if orb_high_gap > 0 and volume5 < 0.75:
                penalty += 7
                filters.append("突破 ORB 但量能不足，假突破風險")
        else:
            orb_break = orb_low_gap <= 0.08
            vwap_ok = vwap_gap <= 0.05
            momentum_ok = slope3 <= 0.10 and slope10 <= 0.25
            if orb_low_gap <= 0.05 and vwap_gap <= 0.03 and volume5 >= 0.65:
                setup_type = "ORB跌破做空"
                filters.append("空方 ORB / VWAP 同向")
            elif vwap_gap <= -0.15 and momentum_ok:
                setup_type = "VWAP下方趨勢做空"
                filters.append("價格跌破 VWAP 且短線動能未轉強")
            elif vwap_gap > 0.7 and slope3 < -0.25 and volume_acc >= 0.9:
                setup_type = "急拉後轉弱做空"
                filters.append("VWAP 上方轉弱型，非低位追空")
            else:
                penalty += 5
                filters.append("做空未完全通過 ORB / VWAP / 動能主要濾網，改為降權觀察")

            if vwap_gap < -1.5 and dist_low30 < 0.20:
                penalty += 12
                filters.append("價格低於 VWAP 太遠且靠近 30K 低點，追空風險")
            if close_location > 0.65 and lower_wick > upper_wick:
                penalty += 5
                filters.append("K 棒收盤位置偏強，下影線支撐較明顯")
            if orb_low_gap < 0 and volume5 < 0.75:
                penalty += 7
                filters.append("跌破 ORB 但量能不足，假跌破風險")

        # 量能濾網：不追低量突破
        if volume5 < 0.55 and volume_acc < 0.70:
            penalty += 8
            filters.append("量能明顯低於短均與長均，波段延續性不足")
        elif volume5 < 0.75:
            penalty += 2
            filters.append("量能略低，降低信心")

        raw_win_rate = self._safe_float(result.get("raw_win_rate", result.get("win_rate")), 0)
        raw_ev = self._safe_float(result.get("raw_expected_value", result.get("expected_value")), -999)
        calibrated_win_rate = max(0.0, raw_win_rate - penalty)
        # 勝率每折扣 1%，期望值額外扣 0.018%。避免看起來正期望但可信度不夠。
        calibrated_ev = raw_ev - penalty * 0.010

        hard_fail = False
        hard_reasons = []
        if blocks:
            hard_fail = True
            hard_reasons.extend(blocks)
        if minute >= 210 and not (calibrated_win_rate >= required_win_rate + 8 and calibrated_ev >= min_expected_value + 0.18 and volume_acc >= 1.15):
            penalty += 3
            filters.append("12:30 後訊號未達極強，改為加重折扣，不直接封鎖")
        if minute >= 150 and not (calibrated_win_rate >= required_win_rate + 5 and calibrated_ev >= min_expected_value + 0.10):
            penalty += 2
            filters.append("11:30 後需要較高勝率與期望值，改為加重折扣")
        if action == "BUY" and vwap_gap > 2.5:
            hard_fail = True
            hard_reasons.append("做多離 VWAP 超過 2.5%，禁止追高")
        if action == "SELL" and vwap_gap < -2.5:
            hard_fail = True
            hard_reasons.append("做空離 VWAP 超過 2.5%，禁止追空")

        professional_pass = not hard_fail
        result.update({
            "raw_win_rate": round(raw_win_rate, 2),
            "raw_expected_value": round(raw_ev, 3),
            "calibrated_win_rate": round(calibrated_win_rate, 2),
            "calibrated_expected_value": round(calibrated_ev, 3),
            "win_rate": round(calibrated_win_rate, 2),
            "expected_value": round(calibrated_ev, 3),
            "filter_penalty": round(penalty, 2),
            "professional_pass": professional_pass,
            "professional_filters": filters[:10],
            "hard_fail_reasons": hard_reasons[:5],
            "setup_type": setup_type,
        })
        return result

    def predict(
        self,
        feature,
        min_expected_value=0.04,
        min_win_rate=None,
        min_sample_count=20,
        stop_pct=0.7,
        take_pct=1.8,
        cost_pct=0.435,
        safety_margin=2.0,
        use_professional_filters=True,
    ):
        buy = self.predict_action(feature, "BUY")
        sell = self.predict_action(feature, "SELL")

        required_win_rate = self.required_win_rate_pct(stop_pct, take_pct, cost_pct, safety_margin)
        if min_win_rate is not None:
            required_win_rate = max(required_win_rate, self._safe_float(min_win_rate, required_win_rate))

        if use_professional_filters:
            buy = self._professional_calibration(buy, feature, "BUY", required_win_rate, min_expected_value)
            sell = self._professional_calibration(sell, feature, "SELL", required_win_rate, min_expected_value)

        def _edge(x):
            return (
                x["expected_value"] * 22
                + (x["win_rate"] - required_win_rate) * 0.85
                + min(x["sample_count"], 120) * 0.025
                + min(x["profit_factor"], 5) * 3
                - x.get("filter_penalty", 0) * 0.55
            )

        buy_edge = _edge(buy)
        sell_edge = _edge(sell)
        buy["edge"] = round(buy_edge, 2)
        sell["edge"] = round(sell_edge, 2)
        for x in [buy, sell]:
            x["required_win_rate"] = required_win_rate
            x["min_expected_value"] = min_expected_value

        allow_buy = (
            buy["professional_pass"]
            and buy["expected_value"] >= min_expected_value
            and buy["win_rate"] >= required_win_rate
            and buy["sample_count"] >= min_sample_count
            and buy["profit_factor"] >= 1.00
        )
        allow_sell = (
            sell["professional_pass"]
            and sell["expected_value"] >= min_expected_value
            and sell["win_rate"] >= required_win_rate
            and sell["sample_count"] >= min_sample_count
            and sell["profit_factor"] >= 1.00
        )

        if allow_buy and buy_edge >= sell_edge:
            decision, chosen = "BUY", buy
        elif allow_sell and sell_edge > buy_edge:
            decision, chosen = "SELL", sell
        else:
            decision, chosen = "WAIT", buy if buy_edge >= sell_edge else sell

        if decision == "WAIT":
            risk_level = "HIGH"
            reason = "專業濾網或扣成本後期望值不足，暫不出手。"
            score = max(0, min(84, int(44 + max(buy_edge, sell_edge) * 0.50)))
        else:
            risk_level = "NORMAL"
            reason = chosen.get("reason", "")
            score = 58 + max(0, chosen["expected_value"]) * 20 + max(0, chosen["win_rate"] - required_win_rate) * 0.85 + min(chosen["profit_factor"], 3) * 4
            if chosen.get("setup_type", "") in ["ORB突破做多", "ORB跌破做空"]:
                score += 4
            score = int(self._clamp(score, 50, 100))

        return {
            "decision": decision,
            "score": score,
            "buy": buy,
            "sell": sell,
            "chosen": chosen,
            "reason": reason,
            "risk_level": risk_level,
            "required_win_rate": required_win_rate,
            "min_expected_value": min_expected_value,
            "stop_pct": round(self._safe_float(stop_pct, 0.7), 3),
            "take_pct": round(self._safe_float(take_pct, 1.8), 3),
            "cost_pct": round(self._safe_float(cost_pct, 0.435), 3),
            "training_days": self.training_days,
            "use_professional_filters": use_professional_filters,
        }
