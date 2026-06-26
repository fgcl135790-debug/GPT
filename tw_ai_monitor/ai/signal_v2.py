def score(df):

    # =========================
    # 1️⃣ 防止 df 還沒資料
    # =========================
    if df is None or len(df) < 20:
        return "WAIT", 0

    price = df["close"].iloc[-1]
    vwap = df["vwap"].iloc[-1]

    # =========================
    # 2️⃣ 防 NaN / None
    # =========================
    if price is None or vwap is None:
        return "WAIT", 0

    try:
        price = float(price)
        vwap = float(vwap)
    except:
        return "WAIT", 0

    # =========================
    # 3️⃣ 策略判斷
    # =========================
    if price > vwap:
        return "BUY", 80

    return "SELL", 50
