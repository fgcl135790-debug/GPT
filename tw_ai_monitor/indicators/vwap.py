import pandas as pd

def volume_ma(volume, n=20):
    return volume.rolling(n).mean()

def volume_spike(volume, n=20):
    ma = volume_ma(volume, n)
    return volume / ma
