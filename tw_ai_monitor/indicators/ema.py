import pandas as pd

def ema(series, span):
    return series.ewm(span=span).mean()
