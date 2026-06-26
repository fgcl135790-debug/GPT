import pandas as pd
import numpy as np


class MarketAnalyzer:

    # =========================
    # EMA
    # =========================

    @staticmethod
    def calculate_ema(prices, span):

        if len(prices) == 0:
            return 0

        return (
            pd.Series(prices)
            .ewm(span=span)
            .mean()
            .iloc[-1]
        )

    # =========================
    # SMA
    # =========================

    @staticmethod
    def calculate_sma(
        prices,
        period,
    ):

        if len(prices) < period:
            return 0

        return (
            pd.Series(prices)
            .rolling(period)
            .mean()
            .iloc[-1]
        )

    # =========================
    # Momentum
    # =========================

    @staticmethod
    def momentum(
        prices,
        period=5,
    ):

        if len(prices) < period + 1:
            return 0

        return (
            prices[-1]
            -
            prices[-period]
        )

    # =========================
    # Price Slope
    # =========================

    @staticmethod
    def price_slope(
        prices,
    ):

        if len(prices) < 10:
            return 0

        x = np.arange(10)
        y = np.array(prices[-10:])

        slope = np.polyfit(
            x,
            y,
            1,
        )[0]

        return slope

    # =========================
    # 波動率
    # =========================

    @staticmethod
    def volatility(
        prices,
    ):

        if len(prices) < 20:
            return 0

        return round(

            pd.Series(prices)
            .pct_change()
            .std()
            * 100,

            2,

        )

    # =========================
    # RSI
    # =========================

    @staticmethod
    def calculate_rsi(
        prices,
        period=14,
    ):

        if len(prices) < period + 1:
            return 50

        delta = pd.Series(prices).diff()

        gain = (
            delta.where(delta > 0, 0)
            .rolling(period)
            .mean()
        )

        loss = (
            (-delta.where(delta < 0, 0))
            .rolling(period)
            .mean()
        )

        rs = gain / loss.replace(0, 1)

        rsi = (

            100

            -

            100 / (1 + rs)

        )

        return round(
            float(rsi.iloc[-1]),
            2,
        )

    # =========================
    # MACD
    # =========================

    @staticmethod
    def calculate_macd(
        prices,
    ):

        if len(prices) < 35:

            return (
                0,
                0,
                0,
            )

        close = pd.Series(prices)

        ema12 = close.ewm(
            span=12,
            adjust=False
        ).mean()

        ema26 = close.ewm(
            span=26,
            adjust=False
        ).mean()

        macd = ema12 - ema26

        signal = macd.ewm(
            span=9,
            adjust=False
        ).mean()

        hist = macd - signal

        return (

            round(float(macd.iloc[-1]), 3),

            round(float(signal.iloc[-1]), 3),

            round(float(hist.iloc[-1]), 3),

        )

    # =========================
    # Volume Trend
    # =========================

    @staticmethod
    def volume_trend(
        volumes,
    ):

        if len(volumes) < 10:

            return "NORMAL"

        recent = (
            sum(volumes[-5:])
            / 5
        )

        previous = (
            sum(volumes[-10:-5])
            / 5
        )

        if recent > previous * 1.5:

            return "UP"

        elif recent < previous * 0.7:

            return "DOWN"

        return "NORMAL"

    # =========================
    # 趨勢判斷
    # =========================

    @staticmethod
    def trend(
        price,
        vwap,
        ema5,
        ema20,
    ):

        if (
            price > vwap
            and
            ema5 > ema20
        ):

            return "多頭"

        elif (
            price < vwap
            and
            ema5 < ema20
        ):

            return "空頭"

        return "盤整"

    # =========================
    # AI交易判斷 PRO
    # =========================

    @staticmethod
    def trading_signal(

        prices,

        price,

        vwap,

        ema5,

        ema20,

        ema60,

        total_bid,

        total_ask,

    ):

        score = 0

        reasons = []

        # ---------------------

        # VWAP

        # ---------------------

        if price > vwap:

            score += 30

            reasons.append(
                "現價站上VWAP"
            )

        else:

            score -= 30

            reasons.append(
                "現價跌破VWAP"
            )

        # ---------------------

        # EMA

        # ---------------------

        if ema5 > ema20:

            score += 25

            reasons.append(
                "EMA5突破EMA20"
            )

        else:

            score -= 25

            reasons.append(
                "EMA5跌破EMA20"
            )

        if ema20 > ema60:

            score += 20

            reasons.append(
                "EMA20站上EMA60"
            )

        else:

            score -= 20

            reasons.append(
                "EMA20跌破EMA60"
            )

        # ---------------------

        # Momentum

        # ---------------------

        if len(prices) >= 5:

            m = MarketAnalyzer.momentum(
                prices
            )

            if m > 2:

                score += 10

                reasons.append(
                    "Momentum向上"
                )

            elif m < -2:

                score -= 10

                reasons.append(
                    "Momentum向下"
                )

            last3 = prices[-3:]

            if (

                last3[2]
                >
                last3[1]
                >
                last3[0]

            ):

                score += 15

                reasons.append(
                    "短線價格連續上升"
                )

            elif (

                last3[2]
                <
                last3[1]
                <
                last3[0]

            ):

                score -= 15

                reasons.append(
                    "短線價格連續下降"
                )

        # ---------------------
        # 委買委賣
        # ---------------------

        bid_ratio = (
            total_bid
            /
            max(total_ask, 1)
        )

        if bid_ratio >= 2:

            score += 30

            reasons.append(
                "委買遠大於委賣"
            )

        elif bid_ratio >= 1.5:

            score += 20

            reasons.append(
                "委買明顯強勢"
            )

        elif bid_ratio >= 1:

            score += 10

            reasons.append(
                "委買略強"
            )

        elif bid_ratio <= 0.5:

            score -= 30

            reasons.append(
                "委賣遠大於委買"
            )

        elif bid_ratio <= 0.7:

            score -= 20

            reasons.append(
                "委賣明顯強勢"
            )

        else:

            score -= 10

            reasons.append(
                "委賣略強"
            )

        # ---------------------
        # Price Slope
        # ---------------------

        slope = MarketAnalyzer.price_slope(
            prices
        )

        if slope > 0.15:

            score += 10

            reasons.append(
                "價格斜率向上"
            )

        elif slope < -0.15:

            score -= 10

            reasons.append(
                "價格斜率向下"
            )

        confidence = min(
            abs(score),
            100
        )

        if score >= 60:

            action = "做多"

        elif score <= -60:

            action = "做空"

        else:

            action = "觀望"

        return (

            action,

            confidence,

            reasons,

        )

    # =========================
    # AI 趨勢反轉預測 PRO
    # =========================

    @staticmethod
    def reversal_prediction(

        prices,

        price,

        vwap,

        ema5,

        ema20,

        ema60,

        total_bid,

        total_ask,

    ):

        score = 0

        reasons = []

        # ---------------------
        # VWAP
        # ---------------------

        if price > vwap:

            score += 20

            reasons.append(
                "站上VWAP"
            )

        else:

            reasons.append(
                "仍在VWAP下"
            )

        # ---------------------
        # EMA排列
        # ---------------------

        if ema5 > ema20:

            score += 20

            reasons.append(
                "EMA5突破EMA20"
            )

        if ema20 > ema60:

            score += 10

            reasons.append(
                "EMA20維持多頭"
            )

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

        # ---------------------
        # Momentum
        # ---------------------

        if len(prices) >= 5:

            momentum = MarketAnalyzer.momentum(
                prices
            )

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
                    "最近價格開始走高"
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
                    "最近價格持續走弱"
                )

        # ---------------------
        # 委買委賣
        # ---------------------

        bid_ratio = (
            total_bid
            /
            max(total_ask, 1)
        )

        if bid_ratio >= 2:

            score += 25

            reasons.append(
                "委買非常強勢"
            )

        elif bid_ratio >= 1.5:

            score += 15

            reasons.append(
                "委買大於委賣"
            )

        elif bid_ratio <= 0.5:

            score -= 25

            reasons.append(
                "委賣非常強勢"
            )

        elif bid_ratio <= 0.7:

            score -= 15

            reasons.append(
                "委賣大於委買"
            )

        # ---------------------
        # RSI
        # ---------------------

        rsi = MarketAnalyzer.calculate_rsi(
            prices
        )

        if rsi < 30:

            score += 10

            reasons.append(
                f"RSI超賣({rsi})"
            )

        elif rsi > 70:

            score -= 10

            reasons.append(
                f"RSI超買({rsi})"
            )

        # ---------------------
        # MACD
        # ---------------------

        macd, signal_line, hist = (
            MarketAnalyzer.calculate_macd(
                prices
            )
        )

        if hist > 0:

            score += 10

            reasons.append(
                "MACD紅柱"
            )

        elif hist < 0:

            score -= 10

            reasons.append(
                "MACD綠柱"
            )

        # ---------------------
        # Price Slope
        # ---------------------

        slope = MarketAnalyzer.price_slope(
            prices
        )

        if slope > 0.15:

            score += 10

            reasons.append(
                "價格斜率向上"
            )

        elif slope < -0.15:

            score -= 10

            reasons.append(
                "價格斜率向下"
            )

        # ---------------------
        # 機率
        # ---------------------

        probability = max(
            0,
            min(score, 100)
        )

        stars = "⭐" * max(
            1,
            probability // 20
        )

        if probability >= 80:

            signal = "BUY"

            text = "🟢 高機率反轉向上"

        elif probability >= 60:

            signal = "WATCH"

            text = "🟡 有反轉跡象"

        elif probability <= 20:

            signal = "SELL"

            text = "🔴 持續轉弱"

        else:

            signal = "NONE"

            text = "⚪ 尚未形成反轉"

        return (

            signal,

            text,

            probability,

            stars,

            reasons,

        )

