from ai.signal import AISignal
from indicators.technical import Indicators

class Analyzer:

    def __init__(self):
        self.ai = AISignal()
        self.ind = Indicators()

    def run(self, df):
        signal = self.ai.predict(df)

        return {
            "ai_signal": signal,
            "ma5": self.ind.ma(df, 5).iloc[-1],
            "ma20": self.ind.ma(df, 20).iloc[-1],
        }
