class SignalV2:

    def score(self, df):

        if df is None or len(df) < 5:
            return "WAIT", 0

        price = df["close"].iloc[-1]
        vwap = df["vwap"].iloc[-1] if "vwap" in df else None

        # ❗防呆：避免 None 比 float
        if price is None:
            return "WAIT", 0

        if vwap is None:
            return "WAIT", 10

        if price > vwap:
            return "BUY", 70
        else:
            return "SELL", 30
