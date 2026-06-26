def score(df):

    price = df["close"].iloc[-1]
    vwap = df["vwap"].iloc[-1]

    if price is None or vwap is None:
        return "WAIT", 0

    if price > vwap:
        return "BUY", 80

    return "SELL", 50
