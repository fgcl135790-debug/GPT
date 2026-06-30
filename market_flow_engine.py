from datetime import datetime, time


class MarketFlowEngine:
    FLOW_VERSION = "v3_sim_history_signal_ready"

    HISTORY_KEYS = [
        "price_history",
        "volume_history",
        "vwap_history",
        "time_history",
    ]

    STATE_DEFAULTS = {
        "price_history": [],
        "volume_history": [],
        "vwap_history": [],
        "time_history": [],
        "big_order_log": [],
        "tick": 0,
        "last_serial": None,
        "big_order_last_serial": None,
        "last_stock": None,
        "last_good_quote": None,
        "api_error_message": None,
        "market_flow_version": None,
    }

    @staticmethod
    def safe_float(value, default=0.0):
        try:
            return float(value)
        except Exception:
            return default

    @staticmethod
    def safe_int(value, default=0):
        try:
            return int(round(float(value)))
        except Exception:
            return default

    @staticmethod
    def init_session_state(st):
        for key, default in MarketFlowEngine.STATE_DEFAULTS.items():
            if key not in st.session_state:
                if isinstance(default, list):
                    st.session_state[key] = []
                else:
                    st.session_state[key] = default

        if st.session_state.get("market_flow_version") != MarketFlowEngine.FLOW_VERSION:
            keep_stock = st.session_state.get("last_stock", None)

            MarketFlowEngine.reset_market_state(
                st=st,
                keep_stock=keep_stock,
            )

            st.session_state.market_flow_version = MarketFlowEngine.FLOW_VERSION

    @staticmethod
    def reset_market_state(st, keep_stock=None):
        st.session_state.price_history = []
        st.session_state.volume_history = []
        st.session_state.vwap_history = []
        st.session_state.time_history = []
        st.session_state.big_order_log = []
        st.session_state.tick = 0
        st.session_state.last_serial = None
        st.session_state.big_order_last_serial = None
        st.session_state.last_good_quote = None
        st.session_state.api_error_message = None

        if keep_stock is not None:
            st.session_state.last_stock = keep_stock

    @staticmethod
    def reset_if_stock_changed(st, stock_code):
        old_stock = st.session_state.get("last_stock", None)

        if old_stock != stock_code:
            MarketFlowEngine.reset_market_state(
                st=st,
                keep_stock=stock_code,
            )

    @staticmethod
    def is_tw_regular_session(now):
        if now is None:
            return False

        if now.weekday() >= 5:
            return False

        return time(9, 0) <= now.time() <= time(13, 30)

    @staticmethod
    def normalize_levels(levels):
        result = []

        for item in levels or []:
            if not isinstance(item, dict):
                continue

            price = MarketFlowEngine.safe_float(
                item.get("price")
                or item.get("bid")
                or item.get("ask")
                or 0
            )

            size = MarketFlowEngine.safe_float(
                item.get("size")
                or item.get("volume")
                or item.get("qty")
                or 0
            )

            result.append(
                {
                    "price": price,
                    "size": size,
                }
            )

        while len(result) < 5:
            result.append(
                {
                    "price": 0,
                    "size": 0,
                }
            )

        return result[:5]

    @staticmethod
    def _first_valid(*values):
        for value in values:
            if value is None:
                continue

            if isinstance(value, str) and value.strip() == "":
                continue

            return value

        return None

    @staticmethod
    def _get_trade_dict(quote):
        trade = quote.get("trade", {}) if isinstance(quote, dict) else {}

        if isinstance(trade, dict):
            return trade

        return {}

    @staticmethod
    def _to_datetime(value, fallback=None):
        if isinstance(value, datetime):
            return value

        if value is None:
            return fallback

        try:
            return datetime.fromisoformat(str(value))
        except Exception:
            return fallback

    @staticmethod
    def _build_quote_fingerprint(
        stock_code,
        price,
        volume,
        vwap,
        high,
        low,
        bids,
        asks,
    ):
        bid_1_price = 0
        bid_1_size = 0
        ask_1_price = 0
        ask_1_size = 0

        if bids:
            bid_1_price = MarketFlowEngine.safe_float(bids[0].get("price", 0))
            bid_1_size = MarketFlowEngine.safe_float(bids[0].get("size", 0))

        if asks:
            ask_1_price = MarketFlowEngine.safe_float(asks[0].get("price", 0))
            ask_1_size = MarketFlowEngine.safe_float(asks[0].get("size", 0))

        return (
            f"{stock_code}|"
            f"p={price:.4f}|"
            f"v={volume:.4f}|"
            f"vw={vwap:.4f}|"
            f"h={high:.4f}|"
            f"l={low:.4f}|"
            f"bp={bid_1_price:.4f}|"
            f"bs={bid_1_size:.4f}|"
            f"ap={ask_1_price:.4f}|"
            f"as={ask_1_size:.4f}"
        )

    @staticmethod
    def _build_serial(
        quote,
        stock_code,
        data_source,
        now,
        tick,
        price,
        volume,
        vwap,
        high,
        low,
        bids,
        asks,
    ):
        quote = quote or {}
        trade = MarketFlowEngine._get_trade_dict(quote)

        raw_serial = MarketFlowEngine._first_valid(
            quote.get("serial"),
            quote.get("tick_id"),
            quote.get("tickId"),
            quote.get("tradeTime"),
            quote.get("lastTradeTime"),
            quote.get("lastUpdated"),
            quote.get("time"),
            quote.get("dateTime"),
            trade.get("serial"),
            trade.get("time"),
            trade.get("tradeTime"),
        )

        fingerprint = MarketFlowEngine._build_quote_fingerprint(
            stock_code=stock_code,
            price=price,
            volume=volume,
            vwap=vwap,
            high=high,
            low=low,
            bids=bids,
            asks=asks,
        )

        if data_source == "模擬盤":
            if raw_serial is not None:
                return f"SIM|{stock_code}|{raw_serial}"

            return f"SIM|{stock_code}|tick={tick}|{fingerprint}"

        if raw_serial is not None:
            return f"REAL|{stock_code}|{raw_serial}|{fingerprint}"

        return f"REAL|{fingerprint}"

    @staticmethod
    def normalize_quote(
        quote,
        stock_code,
        now=None,
        data_source=None,
        tick=None,
    ):
        quote = quote or {}
        now = now or datetime.now()
        trade = MarketFlowEngine._get_trade_dict(quote)

        name = (
            quote.get("name")
            or quote.get("stock_name")
            or quote.get("symbolName")
            or quote.get("symbol_name")
            or stock_code
        )

        price = MarketFlowEngine.safe_float(
            MarketFlowEngine._first_valid(
                quote.get("price"),
                quote.get("lastPrice"),
                quote.get("closePrice"),
                quote.get("close"),
                trade.get("price"),
                0,
            )
        )

        vwap = MarketFlowEngine.safe_float(
            MarketFlowEngine._first_valid(
                quote.get("vwap"),
                quote.get("avgPrice"),
                quote.get("averagePrice"),
                price,
            )
        )

        if vwap <= 0:
            vwap = price

        volume = MarketFlowEngine.safe_float(
            MarketFlowEngine._first_valid(
                quote.get("last_size"),
                quote.get("lastSize"),
                quote.get("last_size_lot"),
                quote.get("volume"),
                quote.get("size"),
                trade.get("size"),
                trade.get("volume"),
                0,
            )
        )

        high = MarketFlowEngine.safe_float(
            MarketFlowEngine._first_valid(
                quote.get("high"),
                quote.get("highPrice"),
                price,
            )
        )

        low = MarketFlowEngine.safe_float(
            MarketFlowEngine._first_valid(
                quote.get("low"),
                quote.get("lowPrice"),
                price,
            )
        )

        bids = MarketFlowEngine.normalize_levels(
            quote.get("bids") or []
        )

        asks = MarketFlowEngine.normalize_levels(
            quote.get("asks") or []
        )

        serial = MarketFlowEngine._build_serial(
            quote=quote,
            stock_code=stock_code,
            data_source=data_source,
            now=now,
            tick=tick,
            price=price,
            volume=volume,
            vwap=vwap,
            high=high,
            low=low,
            bids=bids,
            asks=asks,
        )

        if data_source == "真實盤":
            market_status = (
                "盤中"
                if MarketFlowEngine.is_tw_regular_session(now)
                else "休市"
            )

        elif data_source == "模擬盤":
            market_status = "模擬"

        else:
            market_status = "未知"

        return {
            "name": name,
            "stock_code": stock_code,
            "price": price,
            "vwap": vwap,
            "volume": volume,
            "high": high,
            "low": low,
            "bids": bids,
            "asks": asks,
            "serial": str(serial),
            "market_status": market_status,
            "raw": quote,
        }

    @staticmethod
    def load_history_from_quote(st, quote, now, max_len=500):
        history = quote.get("history", [])

        if not history:
            return False

        prices = []
        volumes = []
        vwaps = []
        times = []

        for item in history[-max_len:]:
            if not isinstance(item, dict):
                continue

            price = MarketFlowEngine.safe_float(
                item.get("price")
                or item.get("close")
                or item.get("lastPrice")
                or 0
            )

            if price <= 0:
                continue

            volume = MarketFlowEngine.safe_float(
                item.get("volume")
                or item.get("last_size")
                or item.get("lastSize")
                or 0
            )

            vwap = MarketFlowEngine.safe_float(
                item.get("vwap")
                or item.get("avgPrice")
                or price
            )

            if vwap <= 0:
                vwap = price

            item_time = MarketFlowEngine._to_datetime(
                item.get("time"),
                fallback=now,
            )

            prices.append(price)
            volumes.append(volume)
            vwaps.append(vwap)
            times.append(item_time)

        if not prices:
            return False

        st.session_state.price_history = prices
        st.session_state.volume_history = volumes
        st.session_state.vwap_history = vwaps
        st.session_state.time_history = times

        return True

    @staticmethod
    def append_history(st, price, volume, vwap, now, serial, max_len=500):
        if st.session_state.get("last_serial") == serial:
            return False

        st.session_state.last_serial = serial

        st.session_state.price_history.append(
            MarketFlowEngine.safe_float(price)
        )

        st.session_state.volume_history.append(
            MarketFlowEngine.safe_float(volume)
        )

        st.session_state.vwap_history.append(
            MarketFlowEngine.safe_float(vwap)
        )

        st.session_state.time_history.append(now)

        MarketFlowEngine.trim_and_align_history(
            st=st,
            max_len=max_len,
        )

        return True

    @staticmethod
    def trim_and_align_history(st, max_len=500):
        for key in MarketFlowEngine.HISTORY_KEYS:
            if key not in st.session_state:
                st.session_state[key] = []

        lengths = [
            len(st.session_state.price_history),
            len(st.session_state.volume_history),
            len(st.session_state.vwap_history),
            len(st.session_state.time_history),
        ]

        min_len = min(lengths) if lengths else 0

        if min_len <= 0:
            st.session_state.price_history = []
            st.session_state.volume_history = []
            st.session_state.vwap_history = []
            st.session_state.time_history = []
            return

        min_len = min(min_len, max_len)

        st.session_state.price_history = st.session_state.price_history[-min_len:]
        st.session_state.volume_history = st.session_state.volume_history[-min_len:]
        st.session_state.vwap_history = st.session_state.vwap_history[-min_len:]
        st.session_state.time_history = st.session_state.time_history[-min_len:]

    @staticmethod
    def get_series(st):
        MarketFlowEngine.trim_and_align_history(st)

        return {
            "prices": st.session_state.price_history,
            "volumes": st.session_state.volume_history,
            "vwaps": st.session_state.vwap_history,
            "times": st.session_state.time_history,
        }

    @staticmethod
    def build_snapshot(
        st,
        quote,
        stock_code,
        now,
        data_source=None,
    ):
        q = MarketFlowEngine.normalize_quote(
            quote=quote,
            stock_code=stock_code,
            now=now,
            data_source=data_source,
            tick=st.session_state.get("tick", None),
        )

        did_load_history = False

        if data_source == "模擬盤":
            did_load_history = MarketFlowEngine.load_history_from_quote(
                st=st,
                quote=quote,
                now=now,
            )

        if did_load_history:
            st.session_state.last_serial = q["serial"]
            did_append = True

        else:
            did_append = MarketFlowEngine.append_history(
                st=st,
                price=q["price"],
                volume=q["volume"],
                vwap=q["vwap"],
                now=now,
                serial=q["serial"],
            )

        series = MarketFlowEngine.get_series(st)

        return {
            "quote": q,
            "name": q["name"],
            "stock_code": q["stock_code"],
            "price": q["price"],
            "vwap": q["vwap"],
            "volume": q["volume"],
            "high": q["high"],
            "low": q["low"],
            "bids": q["bids"],
            "asks": q["asks"],
            "serial": q["serial"],
            "market_status": q["market_status"],
            "did_append": did_append,
            "prices": series["prices"],
            "volumes": series["volumes"],
            "vwaps": series["vwaps"],
            "times": series["times"],
        }
