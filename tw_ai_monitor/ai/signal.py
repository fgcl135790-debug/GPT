class AISignal:

    def predict(self, df):
        close = df["close"]

        ma5 = close.rolling(5).mean()
        ma20 = close.rolling(20).mean()

        rsi = self._rsi(close)

        if ma5.iloc[-1] > ma20.iloc[-1] and rsi.iloc[-1] < 70:
            return {
                "signal": "做多 📈",
                "confidence": 0.75
            }

        elif ma5.iloc[-1] < ma20.iloc[-1] and rsi.iloc[-1] > 30:
            return {
                "signal": "做空 📉",
                "confidence": 0.72
            }

        return {
            "signal": "觀望 ⏸️",
            "confidence": 0.5
        }

    def _rsi(self, close, period=14):
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()

        rs = gain / loss
        return 100 - (100 / (1 + rs))
