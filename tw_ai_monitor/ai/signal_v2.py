def score(df):

    if df is None or len(df) == 0:
        return "WAIT", 0

    price = df["close"].iloc[-1]

    # 假 VWAP（避免缺欄位）
    vwap = price

    if price is None or vwap is None:
        return "WAIT", 0

    if price > vwap:
        return "BUY", 80

    return "SELL", 50
