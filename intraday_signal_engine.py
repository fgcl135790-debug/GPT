import math
from datetime import datetime

from tape_flow_engine import TapeFlowEngine
from orderbook_flow_engine import OrderBookFlowEngine
from market_context_engine import MarketContextEngine
from adaptive_risk_engine import AdaptiveRiskEngine
from signal_quality_engine import SignalQualityEngine
from streak_volume_engine import StreakVolumeEngine


class IntradaySignalEngine:
    """
    專業即時結構 AI v2。

    不訓練、不偷看未來、不用每日候選。
    每一根 K 只使用當下以前資料，並把專業當沖會看的資料分層：
    - ORB / VWAP / 動能斜率
    - Tape Flow 主動買賣量 proxy
    - 五檔委託簿壓力（真實盤有五檔；歷史回測用中性）
    - 盤勢分類：趨勢盤 / VWAP 震盪 / 低波動盤
    - 動態停損停利：依 ATR / ORB / 當日波動調整

    這版的目的不是硬湊每天交易，而是讓 AI 判斷更多「當下已知的盤中結構」，
    避免只靠 1 分 K 技術指標慢半拍。
    """

    DEFAULT_STOP_PCT = 0.7
    DEFAULT_TAKE_PCT = 1.8
    DEFAULT_COST_PCT = 0.435

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
    def _pct(now, prev):
        now = IntradaySignalEngine._safe_float(now)
        prev = IntradaySignalEngine._safe_float(prev)
        if prev <= 0:
            return 0.0
        return (now / prev - 1.0) * 100.0

    @staticmethod
    def _avg(values, default=0.0):
        vals = [IntradaySignalEngine._safe_float(v) for v in values if v is not None]
        if not vals:
            return default
        return sum(vals) / len(vals)

    @staticmethod
    def _clamp(value, low, high):
        return max(low, min(high, value))


    @staticmethod
    def _minute_from_time_value(value):
        """
        回傳距離台股 09:00 開盤後幾分鐘。
        重要：不能用「第幾根 K」代替時間，因為 Fugle 歷史資料有時某些日子只從 10:24 之後開始。
        如果用第幾根 K，10:45 會被誤判成 09:21，會讓 10:30~11:00 濾網完全失效。
        """
        if value is None:
            return None
        try:
            if isinstance(value, datetime):
                h, m = value.hour, value.minute
                return h * 60 + m - 9 * 60
        except Exception:
            pass

        s = str(value).strip()
        if not s:
            return None

        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            return dt.hour * 60 + dt.minute - 9 * 60
        except Exception:
            pass

        try:
            part = s.split(" ")[-1]
            if "T" in part:
                part = part.split("T")[-1]
            hh, mm = part.split(":")[:2]
            return int(hh) * 60 + int(mm) - 9 * 60
        except Exception:
            return None

    @staticmethod
    def required_win_rate_pct(stop_pct=0.7, take_pct=1.8, cost_pct=0.435, safety_margin=0.0):
        stop_pct = IntradaySignalEngine._safe_float(stop_pct, 0.7)
        take_pct = IntradaySignalEngine._safe_float(take_pct, 1.8)
        cost_pct = IntradaySignalEngine._safe_float(cost_pct, 0.435)
        win_net = max(take_pct - cost_pct, 0.000001)
        loss_net = stop_pct + cost_pct
        return round((loss_net / max(win_net + loss_net, 0.000001)) * 100 + safety_margin, 2)

    @staticmethod
    def estimate_ev(win_rate_pct, stop_pct=0.7, take_pct=1.8, cost_pct=0.435):
        p = IntradaySignalEngine._clamp(win_rate_pct, 0, 100) / 100.0
        win_net = take_pct - cost_pct
        loss_net = stop_pct + cost_pct
        return p * win_net - (1 - p) * loss_net

    @staticmethod
    def _score_to_win_rate(score, required_win_rate, context_quality=50.0):
        """
        把結構分數轉成保守勝率估計。
        - 55 分附近接近損益兩平以下
        - 70 分才略高於損益兩平
        - 80+ 才視為品質較好
        context_quality 用來反映當日盤勢是否適合交易。
        """
        score = IntradaySignalEngine._safe_float(score)
        context_adj = (IntradaySignalEngine._safe_float(context_quality, 50) - 50.0) * 0.12
        wr = required_win_rate - 4.0 + (score - 55.0) * 0.72 + context_adj
        return IntradaySignalEngine._clamp(wr, 22.0, 84.0)

    @staticmethod
    def _build_features(
        prices,
        volumes,
        opens=None,
        highs=None,
        lows=None,
        vwap_values=None,
        time_values=None,
    ):
        prices = [IntradaySignalEngine._safe_float(x) for x in (prices or [])]
        volumes = [IntradaySignalEngine._safe_float(x) for x in (volumes or [])]
        n = len(prices)
        if n < 16:
            return None

        opens = [IntradaySignalEngine._safe_float(x) for x in (opens or prices)]
        highs = [IntradaySignalEngine._safe_float(x) for x in (highs or prices)]
        lows = [IntradaySignalEngine._safe_float(x) for x in (lows or prices)]
        if len(opens) < n:
            opens = (opens + prices[len(opens):])[:n]
        if len(highs) < n:
            highs = (highs + prices[len(highs):])[:n]
        if len(lows) < n:
            lows = (lows + prices[len(lows):])[:n]

        price = prices[-1]

        clock_minutes = []
        if time_values and len(time_values) >= n:
            for t in list(time_values)[:n]:
                clock_minutes.append(IntradaySignalEngine._minute_from_time_value(t))
        else:
            clock_minutes = [None] * n

        # 用真實時鐘分鐘，不用第幾根 K。
        # 若某天資料從 10:24 才開始，n-1 會把 10:45 誤判為開盤後 21 分鐘，這是前一版 10:30 濾網失效主因。
        minute_index = clock_minutes[-1] if clock_minutes and clock_minutes[-1] is not None else n - 1

        if vwap_values and len(vwap_values) >= n:
            vwap = IntradaySignalEngine._safe_float(vwap_values[-1], price)
        else:
            amount = 0.0
            vol_sum = 0.0
            for p, v in zip(prices, volumes):
                amount += p * max(v, 0)
                vol_sum += max(v, 0)
            vwap = amount / vol_sum if vol_sum > 0 else price

        # ORB 必須用真正 09:00~09:14 的 K，不可用「資料開始後前 15 根」代替。
        # 歷史 K 若缺開盤資料，就標記 orb_ready=False 並降低信心，避免把 10:24~10:38 誤當開盤區間。
        orb_indices = [
            idx for idx, mm in enumerate(clock_minutes)
            if mm is not None and 0 <= mm < 15
        ]
        if orb_indices:
            orb_high = max(highs[idx] for idx in orb_indices)
            orb_low = min(lows[idx] for idx in orb_indices)
            orb_ready = len(orb_indices) >= 8
        else:
            orb_len = min(15, n)
            orb_high = max(highs[:orb_len]) if highs[:orb_len] else price
            orb_low = min(lows[:orb_len]) if lows[:orb_len] else price
            orb_ready = False

        first_clock_minute = next((mm for mm in clock_minutes if mm is not None), None)
        missing_open_data = bool(
            first_clock_minute is not None
            and first_clock_minute > 5
            and minute_index >= 30
        )

        day_high = max(highs)
        day_low = min(lows)
        day_range_pct = (day_high - day_low) / max(price, 0.000001) * 100

        slope_1 = IntradaySignalEngine._pct(price, prices[-2]) if n >= 2 else 0
        slope_3 = IntradaySignalEngine._pct(price, prices[-4]) if n >= 4 else 0
        slope_5 = IntradaySignalEngine._pct(price, prices[-6]) if n >= 6 else 0
        slope_10 = IntradaySignalEngine._pct(price, prices[-11]) if n >= 11 else 0
        slope_20 = IntradaySignalEngine._pct(price, prices[-21]) if n >= 21 else slope_10

        vol_now = volumes[-1] if volumes else 0.0
        vol5 = IntradaySignalEngine._avg(volumes[-6:-1], default=max(vol_now, 1.0))
        vol20 = IntradaySignalEngine._avg(volumes[-21:-1], default=max(vol_now, 1.0))
        recent3 = IntradaySignalEngine._avg(volumes[-3:], default=max(vol_now, 1.0))
        prev10 = IntradaySignalEngine._avg(volumes[-13:-3], default=max(recent3, 1.0))
        volume_ratio_5 = vol_now / max(vol5, 1.0)
        volume_ratio_20 = vol_now / max(vol20, 1.0)
        volume_acceleration = recent3 / max(prev10, 1.0)

        high_now = highs[-1]
        low_now = lows[-1]
        open_now = opens[-1]
        candle_range = max(high_now - low_now, 0.000001)
        close_location = (price - low_now) / candle_range
        upper_wick_pct = (high_now - max(open_now, price)) / max(price, 0.000001) * 100
        lower_wick_pct = (min(open_now, price) - low_now) / max(price, 0.000001) * 100

        pullback_from_high = (day_high - price) / max(price, 0.000001) * 100
        rebound_from_low = (price - day_low) / max(price, 0.000001) * 100

        return {
            "price": price,
            "minute_index": minute_index,
            "clock_minute": minute_index,
            "orb_ready": orb_ready,
            "missing_open_data": missing_open_data,
            "first_clock_minute": first_clock_minute,
            "vwap": vwap,
            "vwap_gap": IntradaySignalEngine._pct(price, vwap),
            "orb_high": orb_high,
            "orb_low": orb_low,
            "orb_high_gap": IntradaySignalEngine._pct(price, orb_high),
            "orb_low_gap": IntradaySignalEngine._pct(price, orb_low),
            "day_high": day_high,
            "day_low": day_low,
            "day_range_pct": day_range_pct,
            "distance_to_high": abs(IntradaySignalEngine._pct(day_high, price)),
            "distance_to_low": abs(IntradaySignalEngine._pct(price, day_low)),
            "pullback_from_high": pullback_from_high,
            "rebound_from_low": rebound_from_low,
            "slope_1": slope_1,
            "slope_3": slope_3,
            "slope_5": slope_5,
            "slope_10": slope_10,
            "slope_20": slope_20,
            "volume_ratio_5": volume_ratio_5,
            "volume_ratio_20": volume_ratio_20,
            "volume_acceleration": volume_acceleration,
            "close_location": close_location,
            "upper_wick_pct": upper_wick_pct,
            "lower_wick_pct": lower_wick_pct,
        }

    @staticmethod
    def _direction_score(feature, action, tape, orderbook, market_context, rest_microstructure=None, streak_volume=None):
        f = feature
        score = 42.0
        reasons = []
        penalties = []

        minute = int(f.get("minute_index", 0))
        vwap_gap = f.get("vwap_gap", 0.0)
        orb_high_gap = f.get("orb_high_gap", 0.0)
        orb_low_gap = f.get("orb_low_gap", 0.0)
        slope1 = f.get("slope_1", 0.0)
        slope3 = f.get("slope_3", 0.0)
        slope5 = f.get("slope_5", 0.0)
        slope10 = f.get("slope_10", 0.0)
        slope20 = f.get("slope_20", 0.0)
        vr5 = f.get("volume_ratio_5", 1.0)
        vr20 = f.get("volume_ratio_20", 1.0)
        vacc = f.get("volume_acceleration", 1.0)
        close_loc = f.get("close_location", 0.5)
        upper_wick = f.get("upper_wick_pct", 0.0)
        lower_wick = f.get("lower_wick_pct", 0.0)
        dist_high = f.get("distance_to_high", 0.0)
        dist_low = f.get("distance_to_low", 0.0)
        day_range = f.get("day_range_pct", 0.0)

        tape_buy = tape.get("buy_pressure", 50)
        tape_sell = tape.get("sell_pressure", 50)
        ob_buy = orderbook.get("buy_pressure", 50)
        ob_sell = orderbook.get("sell_pressure", 50)
        rest_microstructure = rest_microstructure or {}
        streak_volume = streak_volume or {}
        streak_available = bool(streak_volume.get("available", False))
        rest_available = bool(rest_microstructure.get("available", False))
        rest_buy = rest_microstructure.get("buy_pressure", 50)
        rest_sell = rest_microstructure.get("sell_pressure", 50)
        rest_exec_risk = rest_microstructure.get("execution_risk", "")
        rest_fake_bid = rest_microstructure.get("fake_bid_wall_risk", 0)
        rest_fake_ask = rest_microstructure.get("fake_ask_wall_risk", 0)
        rest_slip_buy = rest_microstructure.get("estimated_slippage_pct_buy", 0)
        rest_slip_sell = rest_microstructure.get("estimated_slippage_pct_sell", 0)
        context_trend = market_context.get("trend", "WAIT")
        context_quality = market_context.get("quality", 50)
        regime = market_context.get("regime", "MIXED")
        orb_ready = bool(f.get("orb_ready", False))
        missing_open_data = bool(f.get("missing_open_data", False))

        # 盤勢品質先當底層濾網。
        score += (context_quality - 50) * 0.18

        if missing_open_data:
            score -= 10
            penalties.append("歷史 K 缺少開盤區間，不能把資料前 15 根誤當 ORB，降低信心。")
        elif not orb_ready and minute >= 30:
            score -= 5
            penalties.append("ORB 開盤區間資料不足，突破可信度降低。")
        if day_range < 0.9:
            score -= 7
            penalties.append("當日區間偏小，停利空間不足。")

        if action == "BUY":
            # 三種做多型態：突破、VWAP 拉回再攻、急跌後轉強反彈。
            breakout = orb_ready and orb_high_gap >= -0.03 and slope3 > 0.05
            vwap_reclaim = -0.25 <= vwap_gap <= 0.45 and slope3 > 0.06 and close_loc >= 0.55
            rebound = vwap_gap < -0.25 and slope1 > 0 and slope3 > 0.08 and close_loc >= 0.62 and tape_buy >= 55

            if breakout:
                score += 13
                reasons.append("做多型態：接近或突破 ORB High，短線開始轉強。")
            if orb_high_gap >= 0.05:
                score += 6
                reasons.append("價格已突破 ORB High。")
            if vwap_reclaim:
                score += 12
                reasons.append("做多型態：VWAP 附近拉回後重新轉強。")
            if rebound:
                score += 8
                reasons.append("做多型態：急跌後短線反彈且成交流改善。")
            if vwap_gap >= 0.03:
                score += 6
                reasons.append("價格站上 VWAP。")

            if slope3 > 0.10:
                score += 5
            if slope5 > 0.18:
                score += 5
            if slope10 > 0.30:
                score += 4
            if slope20 > 0.40:
                score += 3
            if close_loc >= 0.62:
                score += 4
            if vr5 >= 1.2 or vacc >= 1.12:
                score += 6
                reasons.append("量能脈衝放大。")
            if vr5 >= 1.7 or vr20 >= 1.5:
                score += 4

            # 連次 / 連量：確認是不是連續攻擊，而不是單根爆量。
            if streak_available:
                adj = streak_volume.get("buy_score_adj", 0)
                score += adj
                if adj > 3:
                    reasons.extend(streak_volume.get("reasons", [])[:2])
                elif adj < -3:
                    penalties.extend(streak_volume.get("reasons", [])[:2])
                if streak_volume.get("buy_streak_count", 0) >= 3 and streak_volume.get("streak_follow_through", 0) >= 0.18:
                    reasons.append("買方連次連量後價格續強。")
                if streak_volume.get("sell_streak_count", 0) >= 2:
                    penalties.append("當下賣方連次較明顯，做多降分。")

            # Tape / Orderbook：有方向就加，反向就扣。
            score += (tape_buy - 50) * 0.22
            score += (ob_buy - 50) * 0.10
            if rest_available:
                score += (rest_buy - 50) * 0.14
                score -= rest_fake_bid * 0.35
                score -= max(0, rest_slip_buy - 0.12) * 18
                if rest_buy >= 60:
                    reasons.append("REST 五檔序列偏多：委買深度/補單速度改善。")
                if rest_fake_bid >= 8:
                    penalties.append("REST 偵測疑似假買牆，做多降低信心。")
                if rest_exec_risk == "HIGH":
                    score -= 8
                    penalties.append("REST 估計成交難度高，做多滑價風險增加。")
                elif rest_exec_risk == "MEDIUM":
                    score -= 3
                    penalties.append("REST 估計成交難度中等，需注意滑價。")
            if tape_buy >= 60:
                reasons.append("成交流偏主動買。")
            if orderbook.get("available") and ob_buy >= 60:
                reasons.append("五檔承接偏強。")
            if context_trend == "BUY":
                score += 5
                reasons.append("盤勢分類偏多，順勢做多加分。")
            elif context_trend == "SELL":
                score -= 6
                penalties.append("盤勢分類偏空，逆勢做多需降分。")

            if vwap_gap < -0.65 and slope3 <= 0:
                score -= 15
                penalties.append("價格仍在 VWAP 下且未轉強，做多風險高。")
            if vwap_gap > 1.75 and dist_high <= 0.30:
                score -= 15
                penalties.append("離 VWAP 過遠且靠近日高，追高風險。")
            if upper_wick > lower_wick * 1.25 and close_loc < 0.50:
                score -= 7
                penalties.append("上影線壓力較大。")
            if tape.get("absorption_risk", 0) >= 12 and tape_buy > tape_sell:
                score -= 6
                penalties.append("放量但價格推不動，疑似上方吸收。")
            if vr5 < 0.5 and vacc < 0.75:
                score -= 7
                penalties.append("量能不足，做多延續性偏弱。")

        else:
            breakout = orb_ready and orb_low_gap <= 0.03 and slope3 < -0.05
            vwap_fail = -0.45 <= vwap_gap <= 0.25 and slope3 < -0.06 and close_loc <= 0.45
            flush = vwap_gap > 0.25 and slope1 < 0 and slope3 < -0.08 and close_loc <= 0.38 and tape_sell >= 55

            if breakout:
                score += 13
                reasons.append("做空型態：接近或跌破 ORB Low，短線開始轉弱。")
            if orb_low_gap <= -0.05:
                score += 6
                reasons.append("價格已跌破 ORB Low。")
            if vwap_fail:
                score += 12
                reasons.append("做空型態：VWAP 附近反彈失敗。")
            if flush:
                score += 8
                reasons.append("做空型態：急拉後轉弱且成交流轉賣。")
            if vwap_gap <= -0.03:
                score += 6
                reasons.append("價格跌破 VWAP。")

            if slope3 < -0.10:
                score += 5
            if slope5 < -0.18:
                score += 5
            if slope10 < -0.30:
                score += 4
            if slope20 < -0.40:
                score += 3
            if close_loc <= 0.38:
                score += 4
            if vr5 >= 1.2 or vacc >= 1.12:
                score += 6
                reasons.append("量能脈衝放大。")
            if vr5 >= 1.7 or vr20 >= 1.5:
                score += 4

            # 連次 / 連量：確認是不是連續攻擊，而不是單根爆量。
            if streak_available:
                adj = streak_volume.get("sell_score_adj", 0)
                score += adj
                if adj > 3:
                    reasons.extend(streak_volume.get("reasons", [])[:2])
                elif adj < -3:
                    penalties.extend(streak_volume.get("reasons", [])[:2])
                if streak_volume.get("sell_streak_count", 0) >= 3 and streak_volume.get("streak_follow_through", 0) >= 0.18:
                    reasons.append("賣方連次連量後價格續弱。")
                if streak_volume.get("buy_streak_count", 0) >= 2:
                    penalties.append("當下買方連次較明顯，做空降分。")

            score += (tape_sell - 50) * 0.22
            score += (ob_sell - 50) * 0.10
            if rest_available:
                score += (rest_sell - 50) * 0.14
                score -= rest_fake_ask * 0.35
                score -= max(0, rest_slip_sell - 0.12) * 18
                if rest_sell >= 60:
                    reasons.append("REST 五檔序列偏空：委賣深度/壓力增加。")
                if rest_fake_ask >= 8:
                    penalties.append("REST 偵測疑似假賣牆，做空降低信心。")
                if rest_exec_risk == "HIGH":
                    score -= 8
                    penalties.append("REST 估計成交難度高，做空滑價風險增加。")
                elif rest_exec_risk == "MEDIUM":
                    score -= 3
                    penalties.append("REST 估計成交難度中等，需注意滑價。")
            if tape_sell >= 60:
                reasons.append("成交流偏主動賣。")
            if orderbook.get("available") and ob_sell >= 60:
                reasons.append("五檔賣壓偏強。")
            if context_trend == "SELL":
                score += 5
                reasons.append("盤勢分類偏空，順勢做空加分。")
            elif context_trend == "BUY":
                score -= 6
                penalties.append("盤勢分類偏多，逆勢做空需降分。")

            if vwap_gap > 0.65 and slope3 >= 0:
                score -= 15
                penalties.append("價格仍在 VWAP 上且未轉弱，做空風險高。")
            if vwap_gap < -1.75 and dist_low <= 0.30:
                score -= 15
                penalties.append("低於 VWAP 過遠且靠近日低，追空風險。")
            if lower_wick > upper_wick * 1.25 and close_loc > 0.50:
                score -= 7
                penalties.append("下影線支撐較明顯。")
            if tape.get("absorption_risk", 0) >= 12 and tape_sell > tape_buy:
                score -= 6
                penalties.append("放量但價格跌不動，疑似下方吸收。")
            if vr5 < 0.5 and vacc < 0.75:
                score -= 7
                penalties.append("量能不足，做空延續性偏弱。")


        # 方向 K 棒品質：不能只看分數。BUY 卻收在 K 棒低位、SELL 卻收在 K 棒高位，
        # 代表當下攻擊沒有被價格確認，前一版很多虧損都來自這種「看起來有方向但收盤位置不好」。
        if action == "BUY":
            if close_loc < 0.35:
                score -= 14
                penalties.append("做多但 K 棒收在低位，攻擊沒有被價格確認。")
            elif close_loc < 0.50 and slope1 <= 0:
                score -= 9
                penalties.append("做多收盤位置偏弱且短線未續強。")
        else:
            if close_loc > 0.65:
                score -= 14
                penalties.append("做空但 K 棒收在高位，賣壓沒有被價格確認。")
            elif close_loc > 0.50 and slope1 >= 0:
                score -= 9
                penalties.append("做空收盤位置偏強且短線未續弱。")

        # 10:30~11:00 在這批 3481 回測中是明顯的洗盤 / 第一波走完區。
        # 不是完全禁止，而是要求「二次攻擊」：量能重新放大、K 棒收在攻擊方向、短斜率同向。
        # 這是即時可判斷的規則，不使用未來結果。
        if 90 <= minute < 120:
            if action == "BUY":
                second_push_ok = (
                    slope1 > 0.02
                    and slope3 > 0.12
                    and close_loc >= 0.62
                    and (vr5 >= 1.35 or vacc >= 1.25)
                    and tape_buy >= 58
                    and vwap_gap <= 1.20
                )
            else:
                second_push_ok = (
                    slope1 < -0.02
                    and slope3 < -0.12
                    and close_loc <= 0.38
                    and (vr5 >= 1.35 or vacc >= 1.25)
                    and tape_sell >= 58
                    and vwap_gap >= -1.20
                )

            if missing_open_data:
                score -= 26
                penalties.append("10:30~11:00 且缺少開盤資料，無法確認是否為二次攻擊，先避開。")
            elif not second_push_ok:
                score -= 24
                penalties.append("10:30~11:00 第一波常已走完；未出現二次量價攻擊，避免追價。")
            else:
                score += 4
                reasons.append("10:30~11:00 仍有二次量價攻擊，允許觀察。")

        # 盤勢延伸後追高 / 追空風險：趨勢盤不是看到同向就追，
        # 已靠近日高/日低且離 VWAP 偏遠時，勝率容易被高估。
        if action == "BUY":
            if minute >= 30 and regime == "TREND_UP" and vwap_gap > 0.55 and dist_high <= 0.45 and slope1 <= 0.05:
                score -= 12
                penalties.append("多頭延伸但靠近日高、離 VWAP 偏遠，疑似追高。")
        else:
            if minute >= 30 and regime == "TREND_DOWN" and vwap_gap < -0.55 and dist_low <= 0.45 and slope1 >= -0.05:
                score -= 12
                penalties.append("空頭延伸但靠近日低、離 VWAP 偏遠，疑似追空。")

        # 時段風險：專業當沖不是完全禁止午盤，但門檻要提高。
        if minute >= 230:
            score -= 9
            penalties.append("12:50 後新倉，停利空間與隔日風險較高。")
        elif minute >= 180:
            score -= 5
            penalties.append("12:00 後新倉，量縮與假突破風險提高。")
        elif minute >= 150:
            score -= 2
            penalties.append("11:30 後新倉，需確認量能延續。")

        score = IntradaySignalEngine._clamp(score, 0, 100)
        return score, reasons, penalties

    @staticmethod
    def analyze(
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
        stop_pct=0.7,
        take_pct=1.8,
        cost_pct=0.435,
        min_score=66,
        min_expected_value=0.02,
        use_adaptive_risk=True,
    ):
        feature = IntradaySignalEngine._build_features(
            prices=prices,
            volumes=volumes,
            opens=opens,
            highs=highs,
            lows=lows,
            vwap_values=vwap_values,
            time_values=time_values,
        )
        if feature is None:
            return IntradaySignalEngine._wait("盤中資料不足，至少需要 16 根 K。")

        tape = TapeFlowEngine.analyze(prices=prices, volumes=volumes)
        streak_volume = StreakVolumeEngine.analyze(
            prices=prices,
            volumes=volumes,
            opens=opens,
            highs=highs,
            lows=lows,
            vwap_values=vwap_values,
        )
        orderbook = OrderBookFlowEngine.analyze(bids=bids, asks=asks, price=feature.get("price"))
        rest_microstructure = rest_microstructure or {}
        if rest_microstructure.get("available"):
            # REST 序列比單次五檔快照更可靠，混合進五檔壓力。
            orderbook["buy_pressure"] = round((orderbook.get("buy_pressure", 50) * 0.45) + (rest_microstructure.get("buy_pressure", 50) * 0.55), 2)
            orderbook["sell_pressure"] = round((orderbook.get("sell_pressure", 50) * 0.45) + (rest_microstructure.get("sell_pressure", 50) * 0.55), 2)
            orderbook["rest_sequence_available"] = True
        market_context = MarketContextEngine.analyze(
            prices=prices,
            volumes=volumes,
            highs=highs,
            lows=lows,
            vwap_values=vwap_values,
        )
        risk_plan = AdaptiveRiskEngine.suggest(
            prices=prices,
            highs=highs,
            lows=lows,
            volumes=volumes,
            base_stop_pct=stop_pct,
            base_take_pct=take_pct,
            cost_pct=cost_pct,
        ) if use_adaptive_risk else {
            "stop_pct": stop_pct,
            "take_pct": take_pct,
            "risk_reward": round(take_pct / max(stop_pct, 0.01), 2),
            "mode": "base",
            "reasons": ["使用固定停損停利。"],
        }

        eff_stop = risk_plan.get("stop_pct", stop_pct)
        eff_take = risk_plan.get("take_pct", take_pct)
        rest_cost_add = IntradaySignalEngine._safe_float(rest_microstructure.get("effective_cost_add_pct", 0), 0) if rest_microstructure else 0
        effective_cost_pct = cost_pct + min(max(rest_cost_add, 0), 0.35)
        required = IntradaySignalEngine.required_win_rate_pct(eff_stop, eff_take, effective_cost_pct, safety_margin=0.0)

        buy_score, buy_reasons, buy_penalties = IntradaySignalEngine._direction_score(
            feature, "BUY", tape=tape, orderbook=orderbook, market_context=market_context, rest_microstructure=rest_microstructure, streak_volume=streak_volume
        )
        sell_score, sell_reasons, sell_penalties = IntradaySignalEngine._direction_score(
            feature, "SELL", tape=tape, orderbook=orderbook, market_context=market_context, rest_microstructure=rest_microstructure, streak_volume=streak_volume
        )

        context_quality = market_context.get("quality", 50)
        buy_wr = IntradaySignalEngine._score_to_win_rate(buy_score, required, context_quality=context_quality)
        sell_wr = IntradaySignalEngine._score_to_win_rate(sell_score, required, context_quality=context_quality)
        buy_ev = IntradaySignalEngine.estimate_ev(buy_wr, eff_stop, eff_take, effective_cost_pct)
        sell_ev = IntradaySignalEngine.estimate_ev(sell_wr, eff_stop, eff_take, effective_cost_pct)

        buy = {
            "action": "BUY",
            "score": round(buy_score, 2),
            "win_rate": round(buy_wr, 2),
            "expected_value": round(buy_ev, 3),
            "reasons": buy_reasons,
            "penalties": buy_penalties,
            "sample_count": 0,
            "profit_factor": 0,
            "setup_type": "即時結構做多",
        }
        sell = {
            "action": "SELL",
            "score": round(sell_score, 2),
            "win_rate": round(sell_wr, 2),
            "expected_value": round(sell_ev, 3),
            "reasons": sell_reasons,
            "penalties": sell_penalties,
            "sample_count": 0,
            "profit_factor": 0,
            "setup_type": "即時結構做空",
        }

        # 方向選擇：分數 + EV + 成交流方向，避免只靠分數。
        buy_edge = buy_score + buy_ev * 20 + (tape.get("buy_pressure", 50) - 50) * 0.10
        sell_edge = sell_score + sell_ev * 20 + (tape.get("sell_pressure", 50) - 50) * 0.10
        chosen = buy if buy_edge >= sell_edge else sell

        # =========================
        # Signal Quality Gate v1
        # - 用當下以前資料估 MFE / MAE
        # - 避免方向看起來對，但停利空間不足、滑價過高、或不利波動太大的交易。
        # =========================
        quality = SignalQualityEngine.evaluate(
            action=chosen.get("action"),
            chosen=chosen,
            feature=feature,
            tape_flow=tape,
            orderbook_flow=orderbook,
            market_context=market_context,
            risk_plan=risk_plan,
            rest_microstructure=rest_microstructure,
            streak_volume=streak_volume,
            stop_pct=eff_stop,
            take_pct=eff_take,
            cost_pct=effective_cost_pct,
            min_quality_ev=max(min_expected_value, 0.04),
            min_mfe_mae_ratio=1.12,
        )

        # 用品質後分數與 EV 取代原本只看結構分數。
        chosen["raw_score_before_quality"] = chosen.get("score", 0)
        chosen["score"] = round(max(chosen.get("score", 0), quality.get("quality_score", chosen.get("score", 0))), 2)
        chosen["estimated_mfe_pct"] = quality.get("estimated_mfe_pct", 0)
        chosen["estimated_mae_pct"] = quality.get("estimated_mae_pct", 0)
        chosen["mfe_mae_ratio"] = quality.get("mfe_mae_ratio", 0)
        chosen["ev_after_quality"] = quality.get("ev_after_quality", chosen.get("expected_value", 0))
        chosen["quality_adjustment"] = quality.get("quality_adjustment", 0)
        chosen["quality_reasons"] = quality.get("quality_reasons", [])
        chosen["quality_fail_reasons"] = quality.get("quality_fail_reasons", [])

        can_trade = (
            chosen["score"] >= min_score
            and chosen["expected_value"] >= min_expected_value
            and chosen["win_rate"] >= required
            and quality.get("pass_quality_gate", False)
        )

        common_reasons = []
        common_reasons.extend(market_context.get("reasons", [])[:2])
        common_reasons.extend(tape.get("reasons", [])[:2])
        common_reasons.extend(streak_volume.get("reasons", [])[:2])
        if orderbook.get("available"):
            common_reasons.extend(orderbook.get("reasons", [])[:2])
        if rest_microstructure.get("available"):
            common_reasons.extend(rest_microstructure.get("reasons", [])[:3])
        common_reasons.extend(risk_plan.get("reasons", [])[:2])

        base_payload = {
            "buy": buy,
            "sell": sell,
            "chosen": chosen,
            "required_win_rate": required,
            "risk_plan": risk_plan,
            "tape_flow": tape,
            "streak_volume": streak_volume,
            "orderbook_flow": orderbook,
            "rest_microstructure": rest_microstructure,
            "estimated_slippage_pct": round(rest_cost_add, 3),
            "execution_risk": rest_microstructure.get("execution_risk", ""),
            "effective_cost_pct": round(effective_cost_pct, 3),
            "market_context": market_context,
            "feature": feature,
            "signal_quality": quality,
            "estimated_mfe_pct": quality.get("estimated_mfe_pct", 0),
            "estimated_mae_pct": quality.get("estimated_mae_pct", 0),
            "mfe_mae_ratio": quality.get("mfe_mae_ratio", 0),
            "ev_after_quality": quality.get("ev_after_quality", 0),
            "adaptive_stop_pct": eff_stop,
            "adaptive_take_pct": eff_take,
        }

        if not can_trade:
            return {
                **base_payload,
                "decision": "WAIT",
                "action": "WAIT",
                "score": int(max(0, min(86, max(buy_score, sell_score)))),
                "title": "即時結構未達出手標準",
                "reason": "當下成交流、委託簿、盤勢與扣成本期望尚未同步。",
                "reasons": [
                    f"BUY 分數 {buy['score']}｜勝率估 {buy['win_rate']}%｜EV {buy['expected_value']}%",
                    f"SELL 分數 {sell['score']}｜勝率估 {sell['win_rate']}%｜EV {sell['expected_value']}%",
                    f"需求勝率 {required}%｜最低 EV {min_expected_value}%｜最低 Score {min_score}｜有效成本 {effective_cost_pct:.3f}%",
                    f"品質閘門：MFE {quality.get('estimated_mfe_pct', 0)}%｜MAE {quality.get('estimated_mae_pct', 0)}%｜比值 {quality.get('mfe_mae_ratio', 0)}｜品質EV {quality.get('ev_after_quality', 0)}%",
                    *(quality.get("quality_fail_reasons", [])[:4]),
                    *(common_reasons[:4]),
                    *(chosen.get("penalties", [])[:2]),
                ],
                "risk_level": "HIGH",
                "model": "professional_realtime_flow_ai",
            }

        return {
            **base_payload,
            "decision": chosen["action"],
            "action": chosen["action"],
            "score": int(IntradaySignalEngine._clamp(chosen["score"], 0, 100)),
            "title": "專業即時結構 AI 訊號",
            "reason": f"{chosen['action']} 分數 {chosen['score']}，扣成本期望 {chosen['expected_value']}%。",
            "reasons": [
                f"{chosen['action']} 結構分數 {chosen['score']}，估計勝率 {chosen['win_rate']}%，需求 {required}%",
                f"扣成本後期望 {chosen['expected_value']}%｜品質後EV {quality.get('ev_after_quality', 0)}%｜動態停損 {eff_stop}%｜動態停利 {eff_take}%",
                f"MFE/MAE 預估：{quality.get('estimated_mfe_pct', 0)}% / {quality.get('estimated_mae_pct', 0)}%｜比值 {quality.get('mfe_mae_ratio', 0)}",
                *(quality.get("quality_reasons", [])[:4]),
                *(chosen.get("reasons", [])[:3]),
                *(common_reasons[:4]),
                *(chosen.get("penalties", [])[:2]),
            ],
            "risk_level": "NORMAL",
            "model": "professional_realtime_flow_ai",
        }

    @staticmethod
    def _wait(reason):
        return {
            "decision": "WAIT",
            "action": "WAIT",
            "score": 30,
            "title": "等待確認",
            "reason": reason,
            "reasons": [reason],
            "buy": {},
            "sell": {},
            "chosen": {},
            "required_win_rate": 0,
            "risk_level": "HIGH",
        }
