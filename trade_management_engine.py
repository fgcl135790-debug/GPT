class TradeManagementEngine:
    """
    進場後管理 v2：保守出場版。

    v1 的問題：
    - 浮盈只要回吐到接近 0 就出場，扣掉手續費後反而變成成本損。
    - 反向 K 棒太早停損，容易把本來後面會轉好的單先砍掉。

    v2 原則：
    - 不再把「小浮盈回吐到 0」當成出場理由。
    - 只有在扣成本後仍可能保住正報酬時，才啟動浮盈保護。
    - 提早停損只處理明顯錯單，不處理正常洗盤。
    """

    @staticmethod
    def _f(value, default=0.0):
        try:
            return float(value)
        except Exception:
            return default

    @staticmethod
    def check_exit(
        action,
        entry_price,
        current_candle,
        bars_held,
        best_favorable_pct=0.0,
        no_progress_bars=6,
        min_progress_pct=0.25,
        protect_after_pct=1.05,
        protect_floor_pct=0.55,
        cost_pct=0.435,
    ):
        action = str(action or "").upper()
        entry_price = max(TradeManagementEngine._f(entry_price), 0.000001)
        close = TradeManagementEngine._f(current_candle.get("close"), entry_price)
        high = TradeManagementEngine._f(current_candle.get("high"), close)
        low = TradeManagementEngine._f(current_candle.get("low"), close)
        open_price = TradeManagementEngine._f(current_candle.get("open"), close)
        cost_pct = TradeManagementEngine._f(cost_pct, 0.435)

        if action == "BUY":
            current_pnl = (close - entry_price) / entry_price * 100
            intrabar_best = (high - entry_price) / entry_price * 100
            intrabar_worst = (low - entry_price) / entry_price * 100
            reverse_candle = close < open_price and close < (high + low) / 2
        elif action == "SELL":
            current_pnl = (entry_price - close) / entry_price * 100
            intrabar_best = (entry_price - low) / entry_price * 100
            intrabar_worst = (entry_price - high) / entry_price * 100
            reverse_candle = close > open_price and close > (high + low) / 2
        else:
            return None

        best_favorable_pct = max(best_favorable_pct, intrabar_best)

        # 1) 明顯錯單才提早退出。
        # v1 在 -0.12% 就可能提早出，太容易被正常洗盤洗掉。
        if (
            bars_held >= no_progress_bars
            and best_favorable_pct < min_progress_pct
            and current_pnl <= -0.45
            and intrabar_worst <= -0.55
        ):
            return {
                "exit": True,
                "reason": "明顯未推進，保守提早退出",
                "exit_price": close,
                "best_favorable_pct": best_favorable_pct,
                "current_pnl_pct": current_pnl,
            }

        # 2) 浮盈保護只保護「扣成本後仍可能是正報酬」的單。
        # 不能把小浮盈回吐到 0 就砍，否則扣成本後一定輸。
        min_net_safe_gross = max(protect_floor_pct, cost_pct + 0.12)
        if (
            best_favorable_pct >= max(protect_after_pct, cost_pct + 0.65)
            and current_pnl >= min_net_safe_gross
            and current_pnl <= best_favorable_pct - 0.65
        ):
            return {
                "exit": True,
                "reason": "浮盈保護出場",
                "exit_price": close,
                "best_favorable_pct": best_favorable_pct,
                "current_pnl_pct": current_pnl,
            }

        # 3) 反向 K 棒只在虧損接近停損且反向明顯時才提前砍。
        if (
            bars_held >= 3
            and reverse_candle
            and current_pnl <= -0.55
            and intrabar_worst <= -0.62
        ):
            return {
                "exit": True,
                "reason": "反向K棒明顯，保守提早停損",
                "exit_price": close,
                "best_favorable_pct": best_favorable_pct,
                "current_pnl_pct": current_pnl,
            }

        return {
            "exit": False,
            "best_favorable_pct": best_favorable_pct,
            "current_pnl_pct": current_pnl,
        }
