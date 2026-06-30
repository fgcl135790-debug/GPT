from collections import deque
from datetime import datetime


class RestMicrostructureEngine:
    """
    REST 可用版微結構引擎。

    這不是 WebSocket 逐筆成交完整版，而是用每次 REST refresh 拿到的 quote / 五檔快照
    建立短時間序列，讓 AI 可以判斷：
    - 五檔買賣壓力是否正在變化
    - 買一 / 賣一是否有補單或撤單
    - 假買牆 / 假賣牆風險
    - 依照五檔厚度估算滑價、成交難度與有效成本

    回測沒有五檔連續資料時會回傳中性值，不會偷看未來。
    """

    MAXLEN = 80

    @staticmethod
    def _safe_float(value, default=0.0):
        try:
            if value is None:
                return default
            return float(value)
        except Exception:
            return default

    @staticmethod
    def _book_total(levels):
        return sum(RestMicrostructureEngine._safe_float(x.get("size", 0)) for x in (levels or []))

    @staticmethod
    def _best_price(levels):
        if not levels:
            return 0.0
        return RestMicrostructureEngine._safe_float(levels[0].get("price", 0))

    @staticmethod
    def _best_size(levels):
        if not levels:
            return 0.0
        return RestMicrostructureEngine._safe_float(levels[0].get("size", 0))

    @staticmethod
    def _slope(values):
        values = [RestMicrostructureEngine._safe_float(x) for x in (values or [])]
        if len(values) < 2:
            return 0.0
        first = values[0]
        last = values[-1]
        base = max(abs(first), 1.0)
        return (last - first) / base * 100.0

    @staticmethod
    def _avg(values, default=0.0):
        values = [RestMicrostructureEngine._safe_float(x) for x in (values or [])]
        if not values:
            return default
        return sum(values) / len(values)

    @staticmethod
    def init_state(st):
        if "rest_micro_history" not in st.session_state:
            st.session_state.rest_micro_history = deque(maxlen=RestMicrostructureEngine.MAXLEN)
        if "rest_micro_last_key" not in st.session_state:
            st.session_state.rest_micro_last_key = None

    @staticmethod
    def reset(st):
        st.session_state.rest_micro_history = deque(maxlen=RestMicrostructureEngine.MAXLEN)
        st.session_state.rest_micro_last_key = None

    @staticmethod
    def update(st, stock_code, serial, price, bids, asks, volume=0, now=None):
        RestMicrostructureEngine.init_state(st)
        key = f"{stock_code}|{serial}"
        if st.session_state.rest_micro_last_key == key:
            return RestMicrostructureEngine.analyze(list(st.session_state.rest_micro_history), price=price, bids=bids, asks=asks)

        st.session_state.rest_micro_last_key = key
        bid_total = RestMicrostructureEngine._book_total(bids)
        ask_total = RestMicrostructureEngine._book_total(asks)
        best_bid = RestMicrostructureEngine._best_price(bids)
        best_ask = RestMicrostructureEngine._best_price(asks)
        bid1_size = RestMicrostructureEngine._best_size(bids)
        ask1_size = RestMicrostructureEngine._best_size(asks)
        spread = max(best_ask - best_bid, 0.0) if best_bid and best_ask else 0.0
        price = RestMicrostructureEngine._safe_float(price)
        spread_pct = spread / max(price, 0.000001) * 100.0
        imbalance = (bid_total - ask_total) / max(bid_total + ask_total, 1.0) * 100.0

        row = {
            "time": now or datetime.now(),
            "stock_code": stock_code,
            "serial": serial,
            "price": price,
            "volume": RestMicrostructureEngine._safe_float(volume),
            "bid_total": bid_total,
            "ask_total": ask_total,
            "best_bid": best_bid,
            "best_ask": best_ask,
            "bid1_size": bid1_size,
            "ask1_size": ask1_size,
            "spread_pct": spread_pct,
            "imbalance": imbalance,
        }
        st.session_state.rest_micro_history.append(row)
        return RestMicrostructureEngine.analyze(list(st.session_state.rest_micro_history), price=price, bids=bids, asks=asks)

    @staticmethod
    def analyze(history, price=0, bids=None, asks=None, order_size_lot=1):
        history = list(history or [])
        price = RestMicrostructureEngine._safe_float(price)
        bid_total = RestMicrostructureEngine._book_total(bids)
        ask_total = RestMicrostructureEngine._book_total(asks)
        best_bid = RestMicrostructureEngine._best_price(bids)
        best_ask = RestMicrostructureEngine._best_price(asks)
        bid1_size = RestMicrostructureEngine._best_size(bids)
        ask1_size = RestMicrostructureEngine._best_size(asks)
        spread = max(best_ask - best_bid, 0.0) if best_bid and best_ask else 0.0
        spread_pct = spread / max(price, 0.000001) * 100.0 if price > 0 else 0.0

        if len(history) < 3:
            return {
                "available": False,
                "mode": "rest_snapshot_neutral",
                "buy_pressure": 50,
                "sell_pressure": 50,
                "orderbook_imbalance": 0,
                "bid_depth_slope": 0,
                "ask_depth_slope": 0,
                "bid1_replenish_rate": 0,
                "ask1_replenish_rate": 0,
                "fake_bid_wall_risk": 0,
                "fake_ask_wall_risk": 0,
                "estimated_slippage_pct_buy": round(spread_pct, 3),
                "estimated_slippage_pct_sell": round(spread_pct, 3),
                "execution_risk": "UNKNOWN",
                "fill_probability": 50,
                "effective_cost_add_pct": round(spread_pct, 3),
                "reasons": ["REST 五檔快照累積不足，微結構暫用中性值。"],
            }

        recent = history[-8:]
        bid_series = [x.get("bid_total", 0) for x in recent]
        ask_series = [x.get("ask_total", 0) for x in recent]
        bid1_series = [x.get("bid1_size", 0) for x in recent]
        ask1_series = [x.get("ask1_size", 0) for x in recent]
        price_series = [x.get("price", 0) for x in recent]

        bid_depth_slope = RestMicrostructureEngine._slope(bid_series)
        ask_depth_slope = RestMicrostructureEngine._slope(ask_series)
        bid1_replenish = RestMicrostructureEngine._slope(bid1_series)
        ask1_replenish = RestMicrostructureEngine._slope(ask1_series)
        imbalance = (bid_total - ask_total) / max(bid_total + ask_total, 1.0) * 100.0
        price_change = 0.0
        if price_series and price_series[0] > 0:
            price_change = (price_series[-1] - price_series[0]) / price_series[0] * 100.0

        # 假牆近似：單邊深度短時間急升又急降，且價格沒有跟方向移動。
        avg_bid1 = RestMicrostructureEngine._avg(bid1_series[:-1], default=max(bid1_size, 1.0))
        avg_ask1 = RestMicrostructureEngine._avg(ask1_series[:-1], default=max(ask1_size, 1.0))
        bid_wall_pull = max(0.0, (avg_bid1 - bid1_size) / max(avg_bid1, 1.0) * 100.0)
        ask_wall_pull = max(0.0, (avg_ask1 - ask1_size) / max(avg_ask1, 1.0) * 100.0)
        fake_bid_wall_risk = 0.0
        fake_ask_wall_risk = 0.0
        if bid_wall_pull > 35 and price_change <= 0.05:
            fake_bid_wall_risk = min(30.0, bid_wall_pull * 0.45)
        if ask_wall_pull > 35 and price_change >= -0.05:
            fake_ask_wall_risk = min(30.0, ask_wall_pull * 0.45)

        buy_pressure = 50.0 + imbalance * 0.18 + bid_depth_slope * 0.10 - ask_depth_slope * 0.08
        sell_pressure = 50.0 - imbalance * 0.18 + ask_depth_slope * 0.10 - bid_depth_slope * 0.08
        buy_pressure -= fake_bid_wall_risk * 0.45
        sell_pressure -= fake_ask_wall_risk * 0.45
        buy_pressure = max(0, min(100, buy_pressure))
        sell_pressure = max(0, min(100, sell_pressure))

        # 滑價/成交難度：spread + 五檔厚度不足 + 單邊壓力反向。
        avg_depth = max((bid_total + ask_total) / 2.0, 1.0)
        order_size_lot = max(RestMicrostructureEngine._safe_float(order_size_lot, 1), 1)
        depth_penalty = max(0.0, order_size_lot / max(avg_depth, 1.0) * 10.0)
        buy_slippage = spread_pct + max(0.0, (ask_total - bid_total) / max(bid_total + ask_total, 1) * 0.15) + depth_penalty
        sell_slippage = spread_pct + max(0.0, (bid_total - ask_total) / max(bid_total + ask_total, 1) * 0.15) + depth_penalty
        effective_add = max(buy_slippage, sell_slippage)
        if spread_pct >= 0.25 or effective_add >= 0.35:
            execution_risk = "HIGH"
            fill_probability = 45
        elif spread_pct >= 0.12 or effective_add >= 0.20:
            execution_risk = "MEDIUM"
            fill_probability = 65
        else:
            execution_risk = "LOW"
            fill_probability = 82

        reasons = []
        if bid_depth_slope > 12:
            reasons.append("REST 五檔序列：委買深度正在增加。")
        if ask_depth_slope > 12:
            reasons.append("REST 五檔序列：委賣深度正在增加。")
        if fake_bid_wall_risk > 8:
            reasons.append("疑似假買牆：買一量快速消失但價格未轉強。")
        if fake_ask_wall_risk > 8:
            reasons.append("疑似假賣牆：賣一量快速消失但價格未轉弱。")
        if execution_risk != "LOW":
            reasons.append(f"成交難度 {execution_risk}：估計額外滑價/成本約 {effective_add:.3f}%。")
        if not reasons:
            reasons.append("REST 五檔微結構正常，未偵測到明顯假牆或高滑價。")

        return {
            "available": True,
            "mode": "rest_snapshot_sequence",
            "buy_pressure": round(buy_pressure, 2),
            "sell_pressure": round(sell_pressure, 2),
            "orderbook_imbalance": round(imbalance, 2),
            "bid_depth_slope": round(bid_depth_slope, 2),
            "ask_depth_slope": round(ask_depth_slope, 2),
            "bid1_replenish_rate": round(bid1_replenish, 2),
            "ask1_replenish_rate": round(ask1_replenish, 2),
            "fake_bid_wall_risk": round(fake_bid_wall_risk, 2),
            "fake_ask_wall_risk": round(fake_ask_wall_risk, 2),
            "estimated_slippage_pct_buy": round(buy_slippage, 3),
            "estimated_slippage_pct_sell": round(sell_slippage, 3),
            "execution_risk": execution_risk,
            "fill_probability": fill_probability,
            "effective_cost_add_pct": round(effective_add, 3),
            "reasons": reasons,
        }
