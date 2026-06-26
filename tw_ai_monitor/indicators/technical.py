import pandas as pd

class Indicators:

    def ma(self, df, n=5):
        return df["close"].rolling(n).mean()

    def rsi(self, df, period=14):
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()

        rs = gain / loss
        return 100 - (100 / (1 + rs))
