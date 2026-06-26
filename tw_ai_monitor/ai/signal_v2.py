def score(df):

    # 🚨 防呆第一層
    if df is None or len(df) == 0:
        return "WAIT", 0

    if "close" not in df:
        return "WAIT", 0

    price = df["close"].iloc[-1]

    # 🚨 vwap 可有可無
    if "vwap" in df:
        vwap = df["vwap"].iloc[-1]
    else:
        vwap = None

    if vwap is None:
        return "WAIT", 10

    if price > vwap:
        return "BUY", 80

    return "SELL", 40
