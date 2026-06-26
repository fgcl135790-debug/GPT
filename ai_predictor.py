import numpy as np


class AIPredictor:

    # =========================
    # AI 綜合評分
    # =========================

    @staticmethod
    def score(

        price,

        vwap,

        ema5,

        ema20,

        ema60,

        rsi,

        macd,

        macd_signal,

        macd_hist,

        total_bid,

        total_ask,

        momentum,

        volume_trend,

        volatility,

    ):

        score = 50

        reasons = []

        # =====================
        # VWAP
        # =====================

        if price > vwap:

            score += 10

            reasons.append(
                "站上VWAP"
            )

        else:

            score -= 10

            reasons.append(
                "跌破VWAP"
            )

        # =====================
        # EMA
        # =====================

        if ema5 > ema20:

            score += 10

            reasons.append(
                "EMA5 > EMA20"
            )

        else:

            score -= 10

            reasons.append(
                "EMA5 < EMA20"
            )

        if ema20 > ema60:

            score += 10

            reasons.append(
                "EMA20 > EMA60"
            )

        else:

            score -= 10

            reasons.append(
                "EMA20 < EMA60"
            )

        # =====================
        # RSI
        # =====================

        if rsi < 30:

            score += 15

            reasons.append(
                "RSI超賣"
            )

        elif rsi > 70:

            score -= 15

            reasons.append(
                "RSI超買"
            )

        elif rsi >= 50:

            score += 5

            reasons.append(
                "RSI偏多"
            )

        else:

            score -= 5

            reasons.append(
                "RSI偏空"
            )

        # =====================
        # MACD
        # =====================

        if macd > macd_signal:

            score += 10

            reasons.append(
                "MACD黃金交叉"
            )

        else:

            score -= 10

            reasons.append(
                "MACD死亡交叉"
            )

        if macd_hist > 0:

            score += 5

            reasons.append(
                "MACD柱體翻紅"
            )

        else:

            score -= 5

            reasons.append(
                "MACD柱體翻綠"
            )

        # =====================
        # Momentum
        # =====================

        if momentum > 2:

            score += 10

            reasons.append(
                "Momentum強勢"
            )

        elif momentum > 0:

            score += 5

            reasons.append(
                "Momentum轉強"
            )

        elif momentum < -2:

            score -= 10

            reasons.append(
                "Momentum轉弱"
            )

        else:

            score -= 5

            reasons.append(
                "Momentum偏空"
            )

        # =====================
        # 委買委賣
        # =====================

        bid_ratio = (

            total_bid

            /

            max(total_ask, 1)

        )

        if bid_ratio >= 2:

            score += 20

            reasons.append(
                "委買遠大於委賣"
            )

        elif bid_ratio >= 1.5:

            score += 15

            reasons.append(
                "委買強勢"
            )

        elif bid_ratio >= 1:

            score += 5

            reasons.append(
                "委買略強"
            )

        elif bid_ratio <= 0.5:

            score -= 20

            reasons.append(
                "委賣遠大於委買"
            )

        elif bid_ratio <= 0.7:

            score -= 15

            reasons.append(
                "委賣強勢"
            )

        else:

            score -= 5

            reasons.append(
                "委賣略強"
            )

              # =====================
        # 成交量趨勢
        # =====================

        if volume_trend == "UP":

            score += 10

            reasons.append(
                "成交量放大"
            )

        elif volume_trend == "DOWN":

            score -= 10

            reasons.append(
                "成交量萎縮"
            )

        # =====================
        # 波動率
        # =====================

        if volatility >= 3:

            score += 5

            reasons.append(
                "波動率增加"
            )

        elif volatility <= 0.5:

            score -= 5

            reasons.append(
                "波動率過低"
            )

        # =====================
        # AI分數限制
        # =====================

        score = int(

            max(

                0,

                min(score, 100)

            )

        )

        # =====================
        # AI建議
        # =====================

        if score >= 85:

            action = "🔥 強烈做多"

        elif score >= 70:

            action = "🟢 做多"

        elif score >= 55:

            action = "🟡 偏多"

        elif score >= 45:

            action = "⚪ 觀望"

        elif score >= 30:

            action = "🟠 偏空"

        else:

            action = "🔴 做空"

        confidence = score

        return (

            action,

            confidence,

            reasons,

        )

      # =========================
    # AI 趨勢反轉預測 v3
    # =========================

    @staticmethod
    def predict_reversal(

        price,

        prices,

        vwap,

        ema5,

        ema20,

        ema60,

        rsi,

        macd,

        macd_signal,

        total_bid,

        total_ask,

        momentum,

    ):

        score = 0

        reasons = []

        # =====================
        # VWAP
        # =====================

        if price > vwap:

            score += 15

            reasons.append(
                "站上VWAP"
            )

        else:

            reasons.append(
                "仍在VWAP下"
            )

        # =====================
        # EMA
        # =====================

        if ema5 > ema20:

            score += 15

            reasons.append(
                "EMA5突破EMA20"
            )

        if ema20 > ema60:

            score += 10

            reasons.append(
                "EMA20維持多頭"
            )

        # =====================
        # RSI
        # =====================

        if rsi < 35:

            score += 15

            reasons.append(
                "RSI超賣"
            )

        elif rsi > 70:

            score -= 15

            reasons.append(
                "RSI超買"
            )

        # =====================
        # MACD
        # =====================

        if macd > macd_signal:

            score += 15

            reasons.append(
                "MACD黃金交叉"
            )

        else:

            score -= 10

            reasons.append(
                "MACD死亡交叉"
            )

        # =====================
        # 最近價格
        # =====================

        if len(prices) >= 5:

            last5 = prices[-5:]

            if (

                last5[-1]
                >
                last5[-2]
                >
                last5[-3]

            ):

                score += 20

                reasons.append(
                    "價格連續走高"
                )

            elif (

                last5[-1]
                <
                last5[-2]
                <
                last5[-3]

            ):

                score -= 20

                reasons.append(
                    "價格連續走弱"
                )

        # =====================
        # 委買委賣
        # =====================

        bid_ratio = (

            total_bid

            /

            max(total_ask, 1)

        )

        if bid_ratio >= 2:

            score += 20

            reasons.append(
                "委買遠大於委賣"
            )

        elif bid_ratio >= 1.5:

            score += 10

            reasons.append(
                "委買強勢"
            )

        elif bid_ratio <= 0.7:

            score -= 15

            reasons.append(
                "委賣強勢"
            )

        # =====================
        # Momentum
        # =====================

        if momentum > 2:

            score += 10

            reasons.append(
                "Momentum向上"
            )

        elif momentum < -2:

            score -= 10

            reasons.append(
                "Momentum向下"
            )

        # =====================
        # 多頭 / 空頭排列
        # =====================

        if ema5 > ema20 > ema60:

            score += 15

            reasons.append(
                "均線多頭排列"
            )

        elif ema5 < ema20 < ema60:

            score -= 15

            reasons.append(
                "均線空頭排列"
            )

        # =====================
        # AI分數限制
        # =====================

        probability = int(

            max(

                0,

                min(score, 100)

            )

        )

        # =====================
        # 星級
        # =====================

        if probability >= 90:

            stars = "⭐⭐⭐⭐⭐"

        elif probability >= 75:

            stars = "⭐⭐⭐⭐"

        elif probability >= 60:

            stars = "⭐⭐⭐"

        elif probability >= 40:

            stars = "⭐⭐"

        else:

            stars = "⭐"

        # =====================
        # AI訊號
        # =====================

        if probability >= 85:

            signal = "BUY"

            text = "🟢 AI判斷：高機率反轉向上"

        elif probability >= 65:

            signal = "WATCH"

            text = "🟡 AI判斷：有反轉跡象"

        elif probability <= 20:

            signal = "SELL"

            text = "🔴 AI判斷：持續轉弱"

        else:

            signal = "NONE"

            text = "⚪ AI判斷：尚未形成反轉"

        return (

            signal,

            text,

            probability,

            stars,

            reasons,

        )
