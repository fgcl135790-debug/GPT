import requests
import pandas as pd

from intraday_label_engine import IntradayLabelEngine
from intraday_profit_model import IntradayProfitModel


class StockModelCache:
    BASE_URL = "https://api.fugle.tw/marketdata/v1.0/stock"

    @staticmethod
    def _cache_key(
        symbol,
        timeframe,
        stop_pct,
        take_pct,
        max_hold_bars,
    ):
        return (
            f"intraday_profit_model|{symbol}|{timeframe}|"
            f"stop{stop_pct}|take{take_pct}|hold{max_hold_bars}"
        )

    @staticmethod
    def fetch_kline(
        api_key,
        symbol,
        timeframe="1",
    ):
        url = f"{StockModelCache.BASE_URL}/historical/candles/{symbol}"

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
            raise RuntimeError("Fugle API KEY 無效或權限不足。")

        if response.status_code == 429:
            raise RuntimeError("Fugle API 請求過多，請稍後再試。")

        if response.status_code >= 400:
            raise RuntimeError(f"Fugle K線 API 錯誤：{response.status_code}")

        payload = response.json()
        data = payload.get("data", [])

        if not data:
            raise RuntimeError("Fugle 沒有回傳 K 線資料。")

        df = pd.DataFrame(data)

        if "date" not in df.columns:
            raise RuntimeError("Fugle K 線資料缺少 date 欄位。")

        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])

        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df = df.dropna(subset=["open", "high", "low", "close"])
        df = df.sort_values("date").reset_index(drop=True)

        return df

    @staticmethod
    def build_model_package(
        kline_df,
        symbol,
        timeframe="1",
        stop_pct=0.7,
        take_pct=1.8,
        max_hold_bars=50,
        cost_pct=0.435,
    ):
        enriched_df, labels_df = IntradayLabelEngine.build_labels(
            kline_df=kline_df,
            stop_pct=stop_pct,
            take_pct=take_pct,
            max_hold_bars=max_hold_bars,
            cost_pct=cost_pct,
            start_minute=15,
            end_minute=250,
        )

        model = IntradayProfitModel(labels_df)

        if enriched_df.empty:
            start_date = ""
            end_date = ""
            trading_days = 0
            rows = 0
        else:
            start_date = str(enriched_df["trade_date"].min())
            end_date = str(enriched_df["trade_date"].max())
            trading_days = int(enriched_df["trade_date"].nunique())
            rows = int(len(enriched_df))

        if labels_df.empty:
            label_rows = 0
            buy_win_rate = 0
            sell_win_rate = 0
        else:
            label_rows = int(len(labels_df))

            buy_df = labels_df[labels_df["action"] == "BUY"]
            sell_df = labels_df[labels_df["action"] == "SELL"]

            buy_win_rate = float((buy_df["pnl_pct"] > 0).mean() * 100) if not buy_df.empty else 0
            sell_win_rate = float((sell_df["pnl_pct"] > 0).mean() * 100) if not sell_df.empty else 0

        return {
            "symbol": str(symbol),
            "timeframe": str(timeframe),
            "stop_pct": float(stop_pct),
            "take_pct": float(take_pct),
            "max_hold_bars": int(max_hold_bars),
            "cost_pct": float(cost_pct),
            "start_date": start_date,
            "end_date": end_date,
            "trading_days": trading_days,
            "kline_rows": rows,
            "label_rows": label_rows,
            "buy_win_rate_all": round(buy_win_rate, 2),
            "sell_win_rate_all": round(sell_win_rate, 2),
            "model": model,
            "labels": labels_df,
            "kline": enriched_df,
        }

    @staticmethod
    def get_or_build(
        st,
        api_key,
        symbol,
        timeframe="1",
        stop_pct=0.7,
        take_pct=1.8,
        max_hold_bars=50,
        cost_pct=0.435,
        force_rebuild=False,
    ):
        if not api_key:
            return None

        key = StockModelCache._cache_key(
            symbol=symbol,
            timeframe=timeframe,
            stop_pct=stop_pct,
            take_pct=take_pct,
            max_hold_bars=max_hold_bars,
        )

        if "stock_model_cache" not in st.session_state:
            st.session_state.stock_model_cache = {}

        if not force_rebuild and key in st.session_state.stock_model_cache:
            return st.session_state.stock_model_cache[key]

        kline_df = StockModelCache.fetch_kline(
            api_key=api_key,
            symbol=symbol,
            timeframe=timeframe,
        )

        package = StockModelCache.build_model_package(
            kline_df=kline_df,
            symbol=symbol,
            timeframe=timeframe,
            stop_pct=stop_pct,
            take_pct=take_pct,
            max_hold_bars=max_hold_bars,
            cost_pct=cost_pct,
        )

        st.session_state.stock_model_cache[key] = package

        return package

    @staticmethod
    def clear_symbol(st, symbol):
        if "stock_model_cache" not in st.session_state:
            return

        remove_keys = [
            key for key in st.session_state.stock_model_cache.keys()
            if f"|{symbol}|" in key
        ]

        for key in remove_keys:
            del st.session_state.stock_model_cache[key]

# Compatibility helper for fast walk-forward backtests.
def _stock_model_cache_build_from_prebuilt(enriched_df, labels_df, symbol, timeframe="1", stop_pct=0.7, take_pct=1.8, max_hold_bars=50, cost_pct=0.435):
    from intraday_profit_model import IntradayProfitModel

    enriched_df = enriched_df.copy() if enriched_df is not None else pd.DataFrame()
    labels_df = labels_df.copy() if labels_df is not None else pd.DataFrame()

    model = IntradayProfitModel(labels_df)

    if enriched_df.empty:
        start_date = ""
        end_date = ""
        trading_days = 0
        rows = 0
    else:
        start_date = str(enriched_df["trade_date"].min()) if "trade_date" in enriched_df.columns else ""
        end_date = str(enriched_df["trade_date"].max()) if "trade_date" in enriched_df.columns else ""
        trading_days = int(enriched_df["trade_date"].nunique()) if "trade_date" in enriched_df.columns else 0
        rows = int(len(enriched_df))

    if labels_df.empty:
        label_rows = 0
        buy_win_rate = 0
        sell_win_rate = 0
    else:
        label_rows = int(len(labels_df))
        buy_df = labels_df[labels_df["action"] == "BUY"]
        sell_df = labels_df[labels_df["action"] == "SELL"]
        buy_win_rate = float((buy_df["pnl_pct"] > 0).mean() * 100) if not buy_df.empty else 0
        sell_win_rate = float((sell_df["pnl_pct"] > 0).mean() * 100) if not sell_df.empty else 0

    return {
        "symbol": str(symbol),
        "timeframe": str(timeframe),
        "stop_pct": float(stop_pct),
        "take_pct": float(take_pct),
        "max_hold_bars": int(max_hold_bars),
        "cost_pct": float(cost_pct),
        "start_date": start_date,
        "end_date": end_date,
        "trading_days": trading_days,
        "kline_rows": rows,
        "label_rows": label_rows,
        "buy_win_rate_all": round(buy_win_rate, 2),
        "sell_win_rate_all": round(sell_win_rate, 2),
        "model": model,
        "labels": labels_df,
        "kline": enriched_df,
    }

StockModelCache.build_model_package_from_prebuilt = staticmethod(_stock_model_cache_build_from_prebuilt)
