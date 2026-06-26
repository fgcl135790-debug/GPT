class SignalV2:

    def score(self, df):

        score = 50

        ema5 = df["ema5"].iloc[-1]
        ema20 = df["ema20"].iloc[-1]
        ema60 = df["ema60"].iloc[-1]
        price = df["close"].iloc[-1]
        vwap = df["vwap"].iloc[-1]
        vol_spike = df["vol_spike"].iloc[-1]

        # 📈 多頭
        if ema5 > ema20 > ema60:
            score += 20

        if price > vwap:
            score += 10

        if vol_spike > 1.5:
            score += 15

        # 📉 空頭
        if ema5 < ema20 < ema60:
            score -= 20

        if price < vwap:
            score -= 10

        if score >= 70:
            return "做多 📈", score

        elif score <= 40:
            return "做空 📉", score

        return "盤整 ⏸", score
