import math


class OrderBookFlowEngine:
    """
    五檔委託簿壓力引擎。

    歷史 K 回測通常沒有五檔資料，所以沒有 bids/asks 時回傳中性值。
    真實盤時使用目前五檔估算：
    - bid / ask depth imbalance
    - best bid/ask 壓力
    - spread 風險
    - 大買牆 / 大賣牆

    之後若要更專業，可以把每次 refresh 的五檔快照存成 history，
    再計算補單、撤單、買牆消失、賣牆被吃掉等變化速度。
    """

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
    def _normalize(levels):
        out = []
        for item in levels or []:
            if not isinstance(item, dict):
                continue
            out.append({
                "price": OrderBookFlowEngine._safe_float(item.get("price"), 0),
                "size": max(0.0, OrderBookFlowEngine._safe_float(item.get("size"), 0)),
            })
        return out[:5]

    @staticmethod
    def _clamp(value, low, high):
        return max(low, min(high, value))

    @staticmethod
    def analyze(bids=None, asks=None, price=None):
        bids = OrderBookFlowEngine._normalize(bids)
        asks = OrderBookFlowEngine._normalize(asks)
        price = OrderBookFlowEngine._safe_float(price, 0)

        if not bids or not asks:
            return {
                "available": False,
                "buy_pressure": 50.0,
                "sell_pressure": 50.0,
                "imbalance": 0.0,
                "spread_pct": 0.0,
                "wall_side": "NONE",
                "wall_ratio": 0.0,
                "reasons": ["沒有五檔資料，委託簿使用中性值。"],
            }

        bid_sizes = [x["size"] for x in bids]
        ask_sizes = [x["size"] for x in asks]
        bid_total = sum(bid_sizes)
        ask_total = sum(ask_sizes)
        total = max(bid_total + ask_total, 1.0)
        imbalance = (bid_total - ask_total) / total

        best_bid = bids[0]["price"] if bids else 0
        best_ask = asks[0]["price"] if asks else 0
        mid = (best_bid + best_ask) / 2 if best_bid > 0 and best_ask > 0 else max(price, 1.0)
        spread_pct = (best_ask - best_bid) / max(mid, 0.000001) * 100 if best_bid > 0 and best_ask > 0 else 0

        max_bid = max(bid_sizes) if bid_sizes else 0
        max_ask = max(ask_sizes) if ask_sizes else 0
        avg_bid = bid_total / max(len(bid_sizes), 1)
        avg_ask = ask_total / max(len(ask_sizes), 1)
        bid_wall_ratio = max_bid / max(avg_bid, 1.0)
        ask_wall_ratio = max_ask / max(avg_ask, 1.0)

        wall_side = "NONE"
        wall_ratio = 0.0
        if bid_wall_ratio >= 2.2 and bid_wall_ratio > ask_wall_ratio:
            wall_side = "BID"
            wall_ratio = bid_wall_ratio
        elif ask_wall_ratio >= 2.2 and ask_wall_ratio > bid_wall_ratio:
            wall_side = "ASK"
            wall_ratio = ask_wall_ratio

        buy_pressure = 50 + imbalance * 42
        sell_pressure = 50 - imbalance * 42

        # 買一量較大且 spread 小，代表短線承接較強；反之賣壓較重。
        if bid_sizes and ask_sizes:
            best_imb = (bid_sizes[0] - ask_sizes[0]) / max(bid_sizes[0] + ask_sizes[0], 1.0)
            buy_pressure += best_imb * 18
            sell_pressure -= best_imb * 18

        if spread_pct > 0.45:
            buy_pressure -= 6
            sell_pressure -= 6

        reasons = []
        if imbalance > 0.18:
            reasons.append("五檔委買量明顯大於委賣量，短線承接偏強。")
        elif imbalance < -0.18:
            reasons.append("五檔委賣量明顯大於委買量，短線賣壓偏強。")
        else:
            reasons.append("五檔委買委賣接近平衡。")

        if wall_side == "BID":
            reasons.append("偵測到相對買牆，需觀察是否持續補單。")
        elif wall_side == "ASK":
            reasons.append("偵測到相對賣牆，需觀察是否被吃掉或撤單。")
        if spread_pct > 0.45:
            reasons.append("買賣價差偏大，滑價與假突破風險提高。")

        return {
            "available": True,
            "buy_pressure": round(OrderBookFlowEngine._clamp(buy_pressure, 0, 100), 2),
            "sell_pressure": round(OrderBookFlowEngine._clamp(sell_pressure, 0, 100), 2),
            "imbalance": round(imbalance, 4),
            "spread_pct": round(spread_pct, 4),
            "wall_side": wall_side,
            "wall_ratio": round(wall_ratio, 2),
            "bid_total": round(bid_total, 2),
            "ask_total": round(ask_total, 2),
            "reasons": reasons,
        }
