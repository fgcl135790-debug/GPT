class SignalEngine:

    def get_signal(self, df):

        if len(df) < 20:
            return "觀望 ⏸", 50

        ema5 = df["ema5"].iloc[-1]
        ema20 = df["ema20"].iloc[-1]
        ema60 = df["ema60"].iloc[-1]
        price = df["close"].iloc[-1]

        score = 50

        # 多頭條件
        if ema5 > ema20 > ema60:
            score += 25

        # 價格在均線上
        if price > ema20:
            score += 15

        # 空頭條件
        if ema5 < ema20 < ema60:
            score -= 25

        if score > 70:
            return "做多 📈", score
        elif score < 40:
            return "做空 📉", score
        else:
            return "盤整 ⏸", score
