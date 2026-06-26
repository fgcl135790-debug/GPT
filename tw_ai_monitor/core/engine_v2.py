import pandas as pd
from indicators.ema import ema

class Engine:

    def build(self, prices):

        df = pd.DataFrame({"close": prices})

        df["ema5"] = ema(df["close"], 5)
        df["ema20"] = ema(df["close"], 20)
        df["ema60"] = ema(df["close"], 60)

        return df
