class TradeAlertEngine:

    @staticmethod
    def _safe_float(value, default=None):
        try:
            return float(value)
        except Exception:
            return default

    @staticmethod
    def _parse_entry(entry):

        if not entry or entry == "-":
            return None, None

        try:
            parts = str(entry).replace(" ", "").split("~")

            if len(parts) != 2:
                return None, None

            low = float(parts[0])
            high = float(parts[1])

            return low, high

        except Exception:
            return None, None

    @staticmethod
    def track(decision, price):

        action = decision.get("action", "WAIT")
        score = decision.get("score", 0)

        price = TradeAlertEngine._safe_float(price, 0)

        entry = decision.get("entry", "-")
        stop_loss = TradeAlertEngine._safe_float(
            decision.get("stop_loss", None)
        )
        take_profit = TradeAlertEngine._safe_float(
            decision.get("take_profit", None)
        )

        entry_low, entry_high = TradeAlertEngine._parse_entry(entry)

        # =========================
        # 無交易訊號
        # =========================

        if action == "WAIT":

            return {
                "level": "WAIT",
                "title": "等待進場",
                "message": "目前沒有明確進場條件，建議先觀察。",
                "detail": "多空條件尚未同步，不建議硬做。",
                "score": score,
            }

        # =========================
        # 資料不足
        # =========================

        if entry_low is None or entry_high is None:

            return {
                "level": "WAIT",
                "title": "等待進場區",
                "message": "目前尚未形成有效進場區。",
                "detail": "請等待 DecisionEngine 給出完整進場、停損、停利。",
                "score": score,
            }

        # =========================
        # BUY 監控
        # =========================

        if action == "BUY":

            if stop_loss is not None and price <= stop_loss:

                return {
                    "level": "DANGER",
                    "title": "觸及多單停損",
                    "message": "現價已跌破多方停損區。",
                    "detail": f"停損價：{stop_loss}，現價：{price}",
                    "score": score,
                }

            if take_profit is not None and price >= take_profit:

                return {
                    "level": "SUCCESS",
                    "title": "多單達成停利",
                    "message": "現價已達到多方停利目標。",
                    "detail": f"停利價：{take_profit}，現價：{price}",
                    "score": score,
                }

            if entry_low <= price <= entry_high:

                return {
                    "level": "ENTRY",
                    "title": "進入多方進場區",
                    "message": "現價已進入 DecisionEngine 建議的多方觀察區。",
                    "detail": f"進場區：{entry_low} ~ {entry_high}",
                    "score": score,
                }

            if price > entry_high:

                return {
                    "level": "WARNING",
                    "title": "多方價格偏高",
                    "message": "現價已高於建議進場區，避免追高。",
                    "detail": f"建議等回測 {entry_low} ~ {entry_high}",
                    "score": score,
                }

            return {
                "level": "WAIT",
                "title": "等待回測進場",
                "message": "多方條件存在，但價格尚未進入理想區。",
                "detail": f"等待回測：{entry_low} ~ {entry_high}",
                "score": score,
            }

        # =========================
        # SELL 監控
        # =========================

        if action == "SELL":

            if stop_loss is not None and price >= stop_loss:

                return {
                    "level": "DANGER",
                    "title": "觸及空單停損",
                    "message": "現價已突破空方停損區。",
                    "detail": f"停損價：{stop_loss}，現價：{price}",
                    "score": score,
                }

            if take_profit is not None and price <= take_profit:

                return {
                    "level": "SUCCESS",
                    "title": "空單達成停利",
                    "message": "現價已達到空方停利目標。",
                    "detail": f"停利價：{take_profit}，現價：{price}",
                    "score": score,
                }

            if entry_low <= price <= entry_high:

                return {
                    "level": "ENTRY",
                    "title": "進入空方進場區",
                    "message": "現價已進入 DecisionEngine 建議的空方觀察區。",
                    "detail": f"進場區：{entry_low} ~ {entry_high}",
                    "score": score,
                }

            if price < entry_low:

                return {
                    "level": "WARNING",
                    "title": "空方價格偏低",
                    "message": "現價已低於建議進場區，避免追空。",
                    "detail": f"建議等反彈：{entry_low} ~ {entry_high}",
                    "score": score,
                }

            return {
                "level": "WAIT",
                "title": "等待反彈進場",
                "message": "空方條件存在，但價格尚未進入理想區。",
                "detail": f"等待反彈：{entry_low} ~ {entry_high}",
                "score": score,
            }

        return {
            "level": "WAIT",
            "title": "等待訊號",
            "message": "目前尚無有效監控狀態。",
            "detail": "-",
            "score": score,
        }
