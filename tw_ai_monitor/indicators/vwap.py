import pandas as pd

def vwap(df):
    return (df["close"] * df["volume"]).cumsum() / df["volume"].cumsum()
