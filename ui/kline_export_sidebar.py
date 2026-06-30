import requests
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots


BASE_URL = "https://api.fugle.tw/marketdata/v1.0/stock"


def _safe_numeric(df, columns):
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def fetch_kline_data(
    api_key,
    symbol,
    timeframe,
    start_date,
    end_date,
):
    url = f"{BASE_URL}/historical/candles/{symbol}"

    headers = {
        "X-API-KEY": api_key,
    }

    params = {
        "timeframe": str(timeframe),
        "fields": "open,high,low,close,volume",
        "sort": "asc",
    }

    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=30,
    )

    if response.status_code == 401:
        raise RuntimeError("API KEY 無效或權限不足。")

    if response.status_code == 429:
        raise RuntimeError("API 請求過多，請稍後再試。")

    if response.status_code >= 400:
        raise RuntimeError(f"Fugle K 線 API 錯誤：{response.status_code}")

    payload = response.json()
    data = payload.get("data", [])

    if not data:
        raise RuntimeError("沒有取得 K 線資料。")

    df = pd.DataFrame(data)

    if "date" not in df.columns:
        raise RuntimeError("Fugle 回傳資料缺少 date 欄位。")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])

    df["trade_date"] = df["date"].dt.strftime("%Y-%m-%d")
    df["time"] = df["date"].dt.strftime("%H:%M")

    df = _safe_numeric(
        df,
        ["open", "high", "low", "close", "volume"],
    )

    if start_date and end_date:
        df = df[
            (df["trade_date"] >= start_date)
            & (df["trade_date"] <= end_date)
        ].copy()

    df = df.sort_values("date").reset_index(drop=True)

    if df.empty:
        raise RuntimeError(
            "篩選日期後沒有資料。可能日期不在 Fugle 近 30 日分K資料範圍內。"
        )

    return df


def add_indicators(df):
    df = df.copy()

    df["ema5"] = df["close"].ewm(span=5, adjust=False).mean()
    df["ema20"] = df["close"].ewm(span=20, adjust=False).mean()
    df["ema60"] = df["close"].ewm(span=60, adjust=False).mean()

    amount = df["close"] * df["volume"]
    volume_sum = df["volume"].cumsum()

    df["vwap"] = amount.cumsum() / volume_sum.replace(0, pd.NA)

    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()

    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]

    return df


def build_kline_html(df, symbol, timeframe, start_date, end_date):
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
            name="K線",
            increasing=dict(
                line=dict(color="#ff5252"),
                fillcolor="#ff5252",
            ),
            decreasing=dict(
                line=dict(color="#00e676"),
                fillcolor="#00e676",
            ),
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["ema5"],
            name="EMA5",
            mode="lines",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["ema20"],
            name="EMA20",
            mode="lines",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["ema60"],
            name="EMA60",
            mode="lines",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["vwap"],
            name="VWAP",
            mode="lines",
            line=dict(dash="dot"),
        ),
        row=1,
        col=1,
    )

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

    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["macd"],
            name="MACD",
            mode="lines",
        ),
        row=3,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["macd_signal"],
            name="Signal",
            mode="lines",
        ),
        row=3,
        col=1,
    )

    fig.update_layout(
        title=f"{symbol}｜{timeframe}分K｜{start_date} ~ {end_date}",
        height=900,
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
        ),
    )

    fig.update_xaxes(
        rangeslider_visible=False,
    )

    html = fig.to_html(
        full_html=True,
        include_plotlyjs="cdn",
    )

    return html


def render_kline_export_sidebar_panel(api_key, stock_code):
    with st.sidebar.expander("🧾 真實K線匯出", expanded=False):

        st.caption("抓 Fugle 歷史分K，匯出 CSV 與 HTML 圖表。")

        if not api_key:
            st.warning("請先輸入 Fugle API KEY。")
            return

        symbol = st.text_input(
            "股票代號",
            value=str(stock_code),
            key="kline_export_symbol",
        )

        timeframe = st.selectbox(
            "K線週期",
            options=["1", "5", "15", "30"],
            index=0,
            format_func=lambda x: f"{x} 分K",
            key="kline_export_timeframe",
        )

        start_date_str = None
        end_date_str = None

        st.caption("Fugle 分K會回傳近 30 日資料，本功能直接匯出全部回傳資料。")

        run_clicked = st.button(
            "抓取並產生K線檔",
            use_container_width=True,
            key="kline_export_run",
        )

        if run_clicked:
            try:
                with st.spinner("正在抓取真實 K 線..."):
                    df = fetch_kline_data(
                        api_key=api_key,
                        symbol=symbol,
                        timeframe=timeframe,
                        start_date=start_date_str,
                        end_date=end_date_str,
                    )

                    df = add_indicators(df)

                    actual_start = df["trade_date"].min()
                    actual_end = df["trade_date"].max()

                    html = build_kline_html(
                        df=df,
                        symbol=symbol,
                        timeframe=timeframe,
                        start_date=actual_start,
                        end_date=actual_end,
                    )

                    csv = df.to_csv(
                        index=False,
                        encoding="utf-8-sig",
                    )

                    st.session_state.kline_export_result = {
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "start_date": actual_start,
                        "end_date": actual_end,
                        "rows": len(df),
                        "csv": csv,
                        "html": html,
                    }

                st.success(f"K線產生完成，共 {len(df)} 筆。")

            except Exception as e:
                st.session_state.kline_export_result = None
                st.error("K線匯出失敗")
                st.exception(e)

        result = st.session_state.get("kline_export_result")

        if not result:
            st.info("尚未產生 K 線檔。")
            return

        symbol = result["symbol"]
        timeframe = result["timeframe"]
        start_text = result["start_date"].replace("-", "")
        end_text = result["end_date"].replace("-", "")

        csv_filename = f"kline_{symbol}_{timeframe}m_{start_text}_{end_text}.csv"
        html_filename = f"kline_{symbol}_{timeframe}m_{start_text}_{end_text}.html"

        st.divider()

        st.caption(
            f"{symbol}｜{timeframe}分K｜"
            f"{result['start_date']} ~ {result['end_date']}｜"
            f"{result['rows']} 筆"
        )

        st.download_button(
            "下載 K線 CSV",
            data=result["csv"],
            file_name=csv_filename,
            mime="text/csv",
            use_container_width=True,
            key="download_kline_csv",
        )

        st.download_button(
            "下載 K線 HTML 圖表",
            data=result["html"],
            file_name=html_filename,
            mime="text/html",
            use_container_width=True,
            key="download_kline_html",
        )
