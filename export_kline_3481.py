import requests
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


API_KEY = "請貼你的 Fugle API KEY"
SYMBOL = "3481"
TIMEFRAME = "1"

START_DATE = "2026-06-22"
END_DATE = "2026-06-26"

URL = f"https://api.fugle.tw/marketdata/v1.0/stock/historical/candles/{SYMBOL}"


def fetch_kline():
    headers = {
        "X-API-KEY": API_KEY,
    }

    params = {
        "timeframe": TIMEFRAME,
        "fields": "open,high,low,close,volume",
        "sort": "asc",
    }

    response = requests.get(
        URL,
        headers=headers,
        params=params,
        timeout=30,
    )

    response.raise_for_status()

    payload = response.json()
    data = payload.get("data", [])

    if not data:
        raise RuntimeError("沒有取得 K 線資料")

    df = pd.DataFrame(data)

    df["date"] = pd.to_datetime(df["date"])
    df["trade_date"] = df["date"].dt.strftime("%Y-%m-%d")
    df["time"] = df["date"].dt.strftime("%H:%M")

    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df[
        (df["trade_date"] >= START_DATE)
        & (df["trade_date"] <= END_DATE)
    ].copy()

    df = df.sort_values("date").reset_index(drop=True)

    if df.empty:
        raise RuntimeError("篩選日期後沒有資料，可能 Fugle 分K只回傳近30日，或日期不在資料範圍內")

    return df


def add_indicators(df):
    df["ema5"] = df["close"].ewm(span=5, adjust=False).mean()
    df["ema20"] = df["close"].ewm(span=20, adjust=False).mean()
    df["ema60"] = df["close"].ewm(span=60, adjust=False).mean()

    amount = df["close"] * df["volume"]
    df["vwap"] = amount.cumsum() / df["volume"].cumsum()

    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]

    return df


def save_chart(df):
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.62, 0.20, 0.18],
        vertical_spacing=0.03,
    )

    fig.add_trace(
        go.Candlestick(
            x=df["date"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="K",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(go.Scatter(x=df["date"], y=df["ema5"], name="EMA5"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["date"], y=df["ema20"], name="EMA20"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["date"], y=df["ema60"], name="EMA60"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["date"], y=df["vwap"], name="VWAP"), row=1, col=1)

    fig.add_trace(
        go.Bar(
            x=df["date"],
            y=df["volume"],
            name="Volume",
        ),
        row=2,
        col=1,
    )

    fig.add_trace(
        go.Bar(
            x=df["date"],
            y=df["macd_hist"],
            name="MACD Hist",
        ),
        row=3,
        col=1,
    )

    fig.add_trace(go.Scatter(x=df["date"], y=df["macd"], name="MACD"), row=3, col=1)
    fig.add_trace(go.Scatter(x=df["date"], y=df["macd_signal"], name="Signal"), row=3, col=1)

    fig.update_layout(
        title=f"{SYMBOL} 1分K {START_DATE} ~ {END_DATE}",
        height=850,
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
    )

    out_html = f"kline_{SYMBOL}_1m_{START_DATE.replace('-', '')}_{END_DATE.replace('-', '')}.html"
    fig.write_html(out_html)

    print(f"已輸出圖表：{out_html}")


def main():
    df = fetch_kline()
    df = add_indicators(df)

    out_csv = f"kline_{SYMBOL}_1m_{START_DATE.replace('-', '')}_{END_DATE.replace('-', '')}.csv"
    df.to_csv(out_csv, index=False, encoding="utf-8-sig")

    print(f"已輸出 CSV：{out_csv}")
    print(f"資料筆數：{len(df)}")
    print(df.head())
    print(df.tail())

    save_chart(df)


if __name__ == "__main__":
    main()
