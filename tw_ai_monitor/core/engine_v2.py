import pandas as pd
from indicators.ema import ema
from indicators.vwap import vwap
from indicators.volume import volume_ma, volume_spike

class EngineV2:

    def build(self, prices, volumes):

        df = pd.DataFrame({
            "close": prices,
            "volume": volumes
        })

        df["ema5"] = ema(df["close"], 5)
        df["ema20"] = ema(df["close"], 20)
        df["ema60"] = ema(df["close"], 60)

        df["vwap"] = vwap(df)
        df["vol_ma"] = volume_ma(df["volume"])
        df["vol_spike"] = volume_spike(df["volume"])

        return df
