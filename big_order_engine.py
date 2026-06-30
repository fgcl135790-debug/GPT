from datetime import datetime


class BigOrderEngine:

    @staticmethod
    def _safe_float(value, default=0.0):
        try:
            return float(value)
        except Exception:
            return default

    @staticmethod
    def _to_lot(volume):
        """
        Fugle last_size 通常是股數。
        1000 股 = 1 張。
        但模擬盤可能直接給張數，所以這裡做保護。
        """
        volume = BigOrderEngine._safe_float(volume)

        if volume >= 1000:
            return round(volume / 1000, 2)

        return round(volume, 2)

    @staticmethod
    def _auto_threshold(volumes):
        """
        自動大單門檻：
        最近 20 筆平均量 x 3
        最低 10 張
        """
        if not volumes:
            return 10

        lots = [
            BigOrderEngine._to_lot(v)
            for v in volumes[-20:]
            if BigOrderEngine._safe_float(v) > 0
        ]

        if not lots:
            return 10

        avg_lot = sum(lots) / len(lots)

        return round(max(10, avg_lot * 3), 1)

    @staticmethod
    def _detect_direction(price, bids, asks, prices):

        price = BigOrderEngine._safe_float(price)

        best_bid = None
        best_ask = None

        if bids:
            best_bid = BigOrderEngine._safe_float(
                bids[0].get("price", 0)
            )

        if asks:
            best_ask = BigOrderEngine._safe_float(
                asks[0].get("price", 0)
            )

        if best_ask and price >= best_ask:
            return "BUY", "主動買進"

        if best_bid and price <= best_bid:
            return "SELL", "主動賣出"

        if len(prices) >= 2:

            prev_price = BigOrderEngine._safe_float(prices[-2])

            if price > prev_price:
                return "BUY", "價格上推"

            if price < prev_price:
                return "SELL", "價格下殺"

        return "UNKNOWN", "方向不明"

    @staticmethod
    def detect(
        stock_code,
        name,
        price,
        volume,
        bids,
        asks,
        prices,
        volumes,
        threshold_lot=None,
    ):

        price = BigOrderEngine._safe_float(price)
        volume_lot = BigOrderEngine._to_lot(volume)

        if threshold_lot is None:
            threshold_lot = BigOrderEngine._auto_threshold(volumes)

        threshold_lot = BigOrderEngine._safe_float(threshold_lot, 10)

        if volume_lot < threshold_lot:
            return None

        direction, direction_text = BigOrderEngine._detect_direction(
            price=price,
            bids=bids,
            asks=asks,
            prices=prices,
        )

        if volume_lot >= threshold_lot * 3:
            strength = "超大單"
        elif volume_lot >= threshold_lot * 1.5:
            strength = "大單"
        else:
            strength = "異常量"

        return {
            "time": datetime.now().strftime("%H:%M:%S"),
            "stock_code": stock_code,
            "name": name,
            "price": price,
            "volume_lot": volume_lot,
            "threshold_lot": threshold_lot,
            "direction": direction,
            "direction_text": direction_text,
            "strength": strength,
        }
