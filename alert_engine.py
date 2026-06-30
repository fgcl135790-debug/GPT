class AlertEngine:

    @staticmethod
    def _safe_int(value, default=0):
        try:
            return int(round(float(value)))
        except Exception:
            return default

    @staticmethod
    def _safe_float(value, default=0.0):
        try:
            return float(value)
        except Exception:
            return default

    @staticmethod
    def _make_alert(
        title,
        message,
        level="info",
        alert_type="general",
        priority=50,
        icon="ℹ️",
    ):
        return {
            "title": title,
            "message": message,
            "level": level,
            "severity": level,
            "type": alert_type,
            "priority": priority,
            "icon": icon,
        }

    @staticmethod
    def _trade_alert_to_alert(trade_alert):
        if not trade_alert:
            return None

        title = str(trade_alert.get("title", "進出場提醒"))
        message = str(trade_alert.get("message", "-"))

        if title in ["", "-", "等待訊號"] and message in ["", "-", "等待訊號"]:
            return None

        level = trade_alert.get("level", "info")

        if "停損" in title or "風險" in title:
            level = "danger"
            icon = "🛑"
            priority = 92

        elif "停利" in title or "達標" in title:
            level = "success"
            icon = "✅"
            priority = 88

        elif "進場" in title or "接近" in title:
            level = "warning"
            icon = "🎯"
            priority = 82

        else:
            icon = "📌"
            priority = 60

        return AlertEngine._make_alert(
            title=title,
            message=message,
            level=level,
            alert_type="trade",
            priority=priority,
            icon=icon,
        )

    @staticmethod
    def _build_multi_period_alerts(decision):
        alerts = []

        action = decision.get("action", "WAIT")
        score = AlertEngine._safe_int(decision.get("score", 0))
        bias = AlertEngine._safe_float(decision.get("bias", 0))

        multi_period = decision.get("multi_period", {}) or {}

        resonance = multi_period.get("resonance", "WAIT")
        status = multi_period.get("status", "盤整觀望")
        confidence = AlertEngine._safe_int(multi_period.get("confidence", 0))
        bull_count = AlertEngine._safe_int(multi_period.get("bull_count", 0))
        bear_count = AlertEngine._safe_int(multi_period.get("bear_count", 0))
        wait_count = AlertEngine._safe_int(multi_period.get("wait_count", 0))

        if resonance in ["BULL_STRONG", "BULL"] and action == "BUY":
            alerts.append(
                AlertEngine._make_alert(
                    title="多方共振成立",
                    message=f"{status}｜多頭週期 {bull_count}、空頭週期 {bear_count}，Score {score}",
                    level="success",
                    alert_type="multi_period",
                    priority=95,
                    icon="🔴",
                )
            )

        elif resonance in ["BEAR_STRONG", "BEAR"] and action == "SELL":
            alerts.append(
                AlertEngine._make_alert(
                    title="空方共振成立",
                    message=f"{status}｜空頭週期 {bear_count}、多頭週期 {bull_count}，Score {score}",
                    level="danger",
                    alert_type="multi_period",
                    priority=95,
                    icon="🟢",
                )
            )

        elif resonance in ["BULL_STRONG", "BULL"] and action == "SELL":
            alerts.append(
                AlertEngine._make_alert(
                    title="做空訊號與多頭週期衝突",
                    message=f"{status}｜多週期偏多，但目前出現做空訊號，避免追空。",
                    level="warning",
                    alert_type="conflict",
                    priority=96,
                    icon="⚠️",
                )
            )

        elif resonance in ["BEAR_STRONG", "BEAR"] and action == "BUY":
            alerts.append(
                AlertEngine._make_alert(
                    title="做多訊號與空頭週期衝突",
                    message=f"{status}｜多週期偏空，但目前出現做多訊號，避免追多。",
                    level="warning",
                    alert_type="conflict",
                    priority=96,
                    icon="⚠️",
                )
            )

        elif resonance == "DIVERGENCE":
            alerts.append(
                AlertEngine._make_alert(
                    title="多週期背離",
                    message=f"多頭 {bull_count}｜空頭 {bear_count}｜觀望 {wait_count}，方向不一致，避免追價。",
                    level="warning",
                    alert_type="divergence",
                    priority=90,
                    icon="⚠️",
                )
            )

        elif resonance == "WAIT":
            if abs(bias) < 4:
                alerts.append(
                    AlertEngine._make_alert(
                        title="多週期尚未共振",
                        message=f"{status}｜共振信心 {confidence}，等待方向確認。",
                        level="info",
                        alert_type="multi_period_wait",
                        priority=45,
                        icon="⏳",
                    )
                )

        return alerts

    @staticmethod
    def _build_fake_break_alert(decision):
        fake_signal = decision.get("fake_signal", "NONE")
        fake_text = str(decision.get("fake_text", ""))

        if fake_signal == "FAKE_BREAKOUT":
            return AlertEngine._make_alert(
                title="疑似假突破",
                message=fake_text or "突破後量能不足，避免追多。",
                level="warning",
                alert_type="fake_breakout",
                priority=94,
                icon="⚠️",
            )

        if fake_signal == "FAKE_BREAKDOWN":
            return AlertEngine._make_alert(
                title="疑似假跌破",
                message=fake_text or "跌破後殺盤不乾脆，避免追空。",
                level="warning",
                alert_type="fake_breakdown",
                priority=94,
                icon="⚠️",
            )

        if fake_signal == "REAL_BREAKOUT":
            return AlertEngine._make_alert(
                title="有效突破",
                message=fake_text or "突破結構較完整，觀察是否延續。",
                level="success",
                alert_type="real_breakout",
                priority=84,
                icon="🔴",
            )

        if fake_signal == "REAL_BREAKDOWN":
            return AlertEngine._make_alert(
                title="有效跌破",
                message=fake_text or "跌破結構較完整，觀察是否續弱。",
                level="danger",
                alert_type="real_breakdown",
                priority=84,
                icon="🟢",
            )

        return None

    @staticmethod
    def _build_score_alert(decision):
        action = decision.get("action", "WAIT")
        score = AlertEngine._safe_int(decision.get("score", 0))
        bias = AlertEngine._safe_float(decision.get("bias", 0))

        if action == "BUY" and score >= 80:
            return AlertEngine._make_alert(
                title="高信心做多監控",
                message=f"Decision Score {score}，多方分數領先 {bias:.0f}。",
                level="success",
                alert_type="score",
                priority=86,
                icon="🔴",
            )

        if action == "SELL" and score >= 80:
            return AlertEngine._make_alert(
                title="高信心做空監控",
                message=f"Decision Score {score}，空方分數領先 {abs(bias):.0f}。",
                level="danger",
                alert_type="score",
                priority=86,
                icon="🟢",
            )

        if score <= 40:
            return AlertEngine._make_alert(
                title="低信心區",
                message=f"Decision Score {score}，訊號可信度不足，避免追價。",
                level="warning",
                alert_type="score_low",
                priority=70,
                icon="⚠️",
            )

        return None

    @staticmethod
    def _build_big_order_alert(big_order_log):
        if not big_order_log:
            return None

        latest = big_order_log[-1]

        direction = latest.get("direction", "UNKNOWN")
        direction_text = latest.get("direction_text", "-")
        volume_lot = latest.get("volume_lot", "-")
        price = latest.get("price", "-")
        strength = latest.get("strength", "-")

        if direction == "BUY":
            return AlertEngine._make_alert(
                title="最新主力偏多大單",
                message=f"{direction_text}｜{volume_lot} 張｜價格 {price}｜強度 {strength}",
                level="success",
                alert_type="big_order",
                priority=78,
                icon="🐋",
            )

        if direction == "SELL":
            return AlertEngine._make_alert(
                title="最新主力偏空大單",
                message=f"{direction_text}｜{volume_lot} 張｜價格 {price}｜強度 {strength}",
                level="danger",
                alert_type="big_order",
                priority=78,
                icon="🐋",
            )

        return AlertEngine._make_alert(
            title="偵測到主力大單",
            message=f"{direction_text}｜{volume_lot} 張｜價格 {price}｜強度 {strength}",
            level="info",
            alert_type="big_order",
            priority=65,
            icon="🐋",
        )

    @staticmethod
    def _dedupe_alerts(alerts):
        result = []
        seen = set()

        for alert in alerts:
            if not alert:
                continue

            key = (
                alert.get("title", ""),
                alert.get("message", ""),
                alert.get("type", ""),
            )

            if key in seen:
                continue

            seen.add(key)
            result.append(alert)

        return result

    @staticmethod
    def build(decision, trade_alert=None, big_order_log=None):
        decision = decision or {}
        big_order_log = big_order_log or []

        alerts = []

        # 1. 多週期共振 / 衝突 / 背離
        alerts.extend(
            AlertEngine._build_multi_period_alerts(decision)
        )

        # 2. 假突破 / 假跌破
        fake_alert = AlertEngine._build_fake_break_alert(decision)

        if fake_alert is not None:
            alerts.append(fake_alert)

        # 3. 交易進出場提醒
        trade_alert_item = AlertEngine._trade_alert_to_alert(trade_alert)

        if trade_alert_item is not None:
            alerts.append(trade_alert_item)

        # 4. Score 風險 / 高信心提醒
        score_alert = AlertEngine._build_score_alert(decision)

        if score_alert is not None:
            alerts.append(score_alert)

        # 5. 主力大單
        big_order_alert = AlertEngine._build_big_order_alert(big_order_log)

        if big_order_alert is not None:
            alerts.append(big_order_alert)

        # 6. 沒有警示時
        if not alerts:
            alerts.append(
                AlertEngine._make_alert(
                    title="監控中",
                    message="目前沒有重大警示，等待更明確的多空訊號。",
                    level="info",
                    alert_type="idle",
                    priority=10,
                    icon="👀",
                )
            )

        alerts = AlertEngine._dedupe_alerts(alerts)

        alerts = sorted(
            alerts,
            key=lambda item: item.get("priority", 0),
            reverse=True,
        )

        return alerts[:5]
