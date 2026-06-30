"""
Fugle WebSocket 即時行情引擎：診斷版。

重點：
- Socket / Auth / Subscribe / Receiving 分層顯示。
- trades / books / candles 分開訂閱與診斷。
- 顯示最近 raw messages，方便判斷是權限、格式、休市或無資料。
- WebSocket 失敗時，主程式仍會用 REST 備援。
"""

from __future__ import annotations

import json
import math
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    import websocket  # websocket-client
except Exception:  # pragma: no cover
    websocket = None


WS_URL = "wss://api.fugle.tw/marketdata/v1.0/stock/streaming"
CHANNELS = ["trades", "books", "candles"]
MAX_CONN_COOLDOWN_SEC = 300


def _is_max_connection_error(message: Any) -> bool:
    text = str(message or "").lower()
    return "maximum number of connections" in text or "connection limit" in text or "too many connections" in text


class _Safe:
    @staticmethod
    def f(value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return default
            x = float(value)
            if math.isnan(x) or math.isinf(x):
                return default
            return x
        except Exception:
            return default

    @staticmethod
    def i(value: Any, default: int = 0) -> int:
        try:
            if value is None:
                return default
            return int(round(float(value)))
        except Exception:
            return default


def _now_ts() -> float:
    return time.time()


def _short_json(obj: Any, max_len: int = 900) -> str:
    try:
        s = json.dumps(obj, ensure_ascii=False, default=str)
    except Exception:
        s = str(obj)
    if len(s) > max_len:
        return s[:max_len] + "..."
    return s


def _norm_levels(levels: Any) -> List[Dict[str, float]]:
    if not isinstance(levels, list):
        return [{"price": 0.0, "size": 0.0} for _ in range(5)]
    result: List[Dict[str, float]] = []
    for item in levels[:5]:
        if isinstance(item, dict):
            result.append({"price": _Safe.f(item.get("price")), "size": _Safe.f(item.get("size"))})
    while len(result) < 5:
        result.append({"price": 0.0, "size": 0.0})
    return result


@dataclass
class _WSState:
    api_key_hash: str = ""
    symbol: str = ""
    enabled: bool = False

    connected: bool = False
    authenticated: bool = False
    auth_status: str = "idle"  # idle / sent / success / failed

    last_event: str = ""
    last_error: str = ""
    last_message_ts: float = 0.0
    started_ts: float = 0.0
    cooldown_until_ts: float = 0.0
    cooldown_reason: str = ""

    subscribed: Dict[str, str] = field(default_factory=dict)
    channel_status: Dict[str, str] = field(default_factory=lambda: {ch: "not_sent" for ch in CHANNELS})
    channel_errors: Dict[str, str] = field(default_factory=dict)
    channel_last_message_ts: Dict[str, float] = field(default_factory=dict)
    subscribe_requests: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    latest_trade: Dict[str, Any] = field(default_factory=dict)
    latest_books: Dict[str, Any] = field(default_factory=dict)
    latest_candle: Dict[str, Any] = field(default_factory=dict)
    trades: deque = field(default_factory=lambda: deque(maxlen=600))
    books: deque = field(default_factory=lambda: deque(maxlen=180))

    raw_events: deque = field(default_factory=lambda: deque(maxlen=80))
    sent_events: deque = field(default_factory=lambda: deque(maxlen=40))


_STATE = _WSState()
_LOCK = threading.RLock()
_WORKER: Optional["_FugleWSWorker"] = None


class _FugleWSWorker:
    def __init__(self, api_key: str, symbol: str, channels: Optional[List[str]] = None):
        self.api_key = str(api_key or "").strip()
        self.symbol = str(symbol or "").strip()
        self.channels = channels or list(CHANNELS)
        self.wsapp = None
        self.thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()

    def start(self):
        if websocket is None:
            with _LOCK:
                _STATE.last_error = "缺少 websocket-client 套件，請確認 requirements.txt。"
                _STATE.enabled = False
            return
        self.thread = threading.Thread(target=self._run, name=f"fugle-ws-{self.symbol}", daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        try:
            if self.wsapp is not None:
                self.wsapp.close()
        except Exception:
            pass

    def _run(self):
        with _LOCK:
            _STATE.started_ts = _now_ts()
            _STATE.connected = False
            _STATE.authenticated = False
            _STATE.auth_status = "idle"
            _STATE.last_error = ""
            _STATE.last_event = "connecting"
            _STATE.enabled = True
            _STATE.channel_status = {ch: "not_sent" for ch in CHANNELS}
            _STATE.channel_errors = {}
            _STATE.channel_last_message_ts = {}
            _STATE.raw_events.clear()
            _STATE.sent_events.clear()

        try:
            self.wsapp = websocket.WebSocketApp(
                WS_URL,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
            )
            self.wsapp.run_forever(ping_interval=20, ping_timeout=10, reconnect=0)
        except Exception as e:
            msg = f"WebSocket 執行失敗：{type(e).__name__}: {e}"
            with _LOCK:
                _STATE.last_error = msg
                _STATE.connected = False
                _STATE.authenticated = False
                _STATE.auth_status = "failed"
                _STATE.last_event = "error"
                if _is_max_connection_error(msg):
                    _STATE.cooldown_until_ts = _now_ts() + MAX_CONN_COOLDOWN_SEC
                    _STATE.cooldown_reason = "Fugle 回覆連線數已達上限，暫停重連，避免越連越多。"

    def _send(self, payload: Dict[str, Any]):
        try:
            with _LOCK:
                _STATE.sent_events.append({"ts": _now_ts(), "payload": payload})
            if self.wsapp:
                self.wsapp.send(json.dumps(payload, ensure_ascii=False))
        except Exception as e:
            with _LOCK:
                _STATE.last_error = f"WebSocket send 失敗：{type(e).__name__}: {e}"

    def _on_open(self, ws):
        with _LOCK:
            _STATE.connected = True
            _STATE.last_event = "connected"
            _STATE.last_message_ts = _now_ts()
            _STATE.auth_status = "sent"
        # Fugle v1.0 raw WebSocket authentication.
        self._send({"event": "auth", "data": {"apikey": self.api_key}})

    def _on_close(self, ws, code, reason):
        with _LOCK:
            _STATE.connected = False
            _STATE.authenticated = False
            _STATE.last_event = "closed"
            if reason:
                _STATE.last_error = f"WebSocket closed: {code} {reason}"

    def _on_error(self, ws, error):
        msg = f"WebSocket error: {error}"
        with _LOCK:
            _STATE.last_error = msg
            _STATE.last_event = "error"
            if _is_max_connection_error(msg):
                _STATE.cooldown_until_ts = _now_ts() + MAX_CONN_COOLDOWN_SEC
                _STATE.cooldown_reason = "Fugle 回覆連線數已達上限，已進入 5 分鐘重連冷卻。"
                _STATE.connected = False
                _STATE.authenticated = False
                _STATE.auth_status = "failed"

    def _subscribe_all(self):
        # 逐一送出，不用 channels 陣列，避免 raw WS 格式不相容。
        for ch in self.channels:
            payload = {"event": "subscribe", "data": {"channel": ch, "symbol": self.symbol}}
            with _LOCK:
                _STATE.channel_status[ch] = "sent"
                _STATE.subscribe_requests[ch] = payload
            self._send(payload)
            time.sleep(0.08)

    def _extract_channel(self, payload: Dict[str, Any], data: Any, fallback: Any = None) -> str:
        for src in [payload, data if isinstance(data, dict) else None, fallback if isinstance(fallback, dict) else None]:
            if isinstance(src, dict):
                ch = src.get("channel")
                if ch:
                    return str(ch)
        return ""

    def _mark_subscribed(self, payload: Dict[str, Any], data: Any):
        items: List[Dict[str, Any]] = []
        if isinstance(data, list):
            items = [x for x in data if isinstance(x, dict)]
        elif isinstance(data, dict):
            items = [data]
        elif isinstance(payload.get("data"), dict):
            items = [payload["data"]]

        with _LOCK:
            if not items:
                # 無 channel 的 subscribed 回覆，先標記最後一個 sent 為 subscribed_pending。
                for ch, status in _STATE.channel_status.items():
                    if status == "sent":
                        _STATE.channel_status[ch] = "subscribed"
                        break
            for item in items:
                ch = str(item.get("channel") or "")
                if ch:
                    _STATE.subscribed[ch] = str(item.get("id") or item.get("symbol") or "subscribed")
                    _STATE.channel_status[ch] = "subscribed"
                    _STATE.channel_errors.pop(ch, None)

    def _handle_error_event(self, payload: Dict[str, Any], data: Any):
        msg = ""
        if isinstance(data, dict):
            msg = str(data.get("message") or data.get("reason") or data.get("error") or "")
        if not msg:
            msg = _short_json(payload, 500)
        ch = self._extract_channel(payload, data)
        with _LOCK:
            _STATE.last_error = msg or "WebSocket error"
            _STATE.last_event = "error"
            if ch:
                _STATE.channel_status[ch] = "failed"
                _STATE.channel_errors[ch] = msg
            elif _STATE.auth_status == "sent" and not _STATE.authenticated:
                _STATE.auth_status = "failed"

    def _on_message(self, ws, message):
        try:
            payload = json.loads(message) if isinstance(message, str) else message
        except Exception:
            with _LOCK:
                _STATE.raw_events.append({"ts": _now_ts(), "raw": str(message)[:1000], "parse_error": True})
            return

        if not isinstance(payload, dict):
            return

        event = payload.get("event") or payload.get("type")
        channel = payload.get("channel")
        data = payload.get("data")
        if data is None:
            data = payload.get("payload") or {}
        ts = _now_ts()

        with _LOCK:
            _STATE.last_message_ts = ts
            _STATE.last_event = str(event or channel or "message")
            _STATE.raw_events.append({"ts": ts, "event": event, "channel": channel, "payload": payload})

        # Auth success from official docs: event=authenticated.
        if event == "authenticated":
            with _LOCK:
                _STATE.authenticated = True
                _STATE.auth_status = "success"
                _STATE.last_error = ""
            self._subscribe_all()
            return

        if event in ["unauthenticated", "authentication_failed"]:
            with _LOCK:
                _STATE.authenticated = False
                _STATE.auth_status = "failed"
                _STATE.last_error = _short_json(payload, 500)
            return

        if event == "subscribed":
            self._mark_subscribed(payload, data)
            return

        if event == "unsubscribed":
            ch = self._extract_channel(payload, data)
            if ch:
                with _LOCK:
                    _STATE.channel_status[ch] = "unsubscribed"
            return

        if event == "error":
            self._handle_error_event(payload, data)
            return

        if event in ["heartbeat", "pong", "ping"]:
            return

        # Fugle market data usually event=data + channel=trades/books/candles.
        if event != "data" and channel not in CHANNELS:
            return
        if not isinstance(data, dict):
            return

        ch = str(channel or data.get("channel") or "")
        sym = str(data.get("symbol") or "")
        if self.symbol and sym and sym != self.symbol:
            return

        if ch in CHANNELS:
            with _LOCK:
                if _STATE.channel_status.get(ch) in ["sent", "subscribed", "not_sent"]:
                    _STATE.channel_status[ch] = "receiving"
                _STATE.channel_last_message_ts[ch] = ts

        if ch == "trades":
            self._handle_trade(data, ts)
        elif ch == "books":
            self._handle_books(data, ts)
        elif ch == "candles":
            with _LOCK:
                _STATE.latest_candle = dict(data)

    def _handle_trade(self, data: Dict[str, Any], ts: float):
        price = _Safe.f(data.get("price"))
        bid = _Safe.f(data.get("bid"))
        ask = _Safe.f(data.get("ask"))
        size = _Safe.f(data.get("size") or data.get("volume"))

        side = "NEUTRAL"
        if ask > 0 and price >= ask:
            side = "BUY"
        elif bid > 0 and price <= bid:
            side = "SELL"
        else:
            with _LOCK:
                prev = _Safe.f((_STATE.latest_trade or {}).get("price"))
            if prev > 0:
                if price > prev:
                    side = "BUY"
                elif price < prev:
                    side = "SELL"

        record = dict(data)
        record.update({"_ts": ts, "side": side, "price": price, "size": size, "bid": bid, "ask": ask})
        with _LOCK:
            _STATE.latest_trade = record
            _STATE.trades.append(record)

    def _handle_books(self, data: Dict[str, Any], ts: float):
        bids = _norm_levels(data.get("bids"))
        asks = _norm_levels(data.get("asks"))
        bid_depth = sum(x.get("size", 0) for x in bids)
        ask_depth = sum(x.get("size", 0) for x in asks)
        best_bid = bids[0]["price"] if bids else 0
        best_ask = asks[0]["price"] if asks else 0
        spread = max(best_ask - best_bid, 0) if best_bid and best_ask else 0
        mid = (best_bid + best_ask) / 2 if best_bid and best_ask else 0
        record = dict(data)
        record.update({
            "_ts": ts,
            "bids": bids,
            "asks": asks,
            "bid_depth": bid_depth,
            "ask_depth": ask_depth,
            "best_bid": best_bid,
            "best_ask": best_ask,
            "spread": spread,
            "spread_pct": (spread / mid * 100) if mid else 0,
        })
        with _LOCK:
            _STATE.latest_books = record
            _STATE.books.append(record)


class WebSocketLiveEngine:
    """Streamlit 用的 Fugle WebSocket 管理器。"""

    @staticmethod
    def _hash_key(api_key: str) -> str:
        s = str(api_key or "")
        if not s:
            return ""
        return f"len:{len(s)}|tail:{s[-4:]}"

    @staticmethod
    def reset(st=None):
        global _WORKER, _STATE
        if _WORKER is not None:
            _WORKER.stop()
        _WORKER = None
        with _LOCK:
            _STATE = _WSState()
        if st is not None:
            st.session_state["ws_live_status"] = {}

    @staticmethod
    def ensure_running(api_key: str, symbol: str, enabled: bool = True) -> Dict[str, Any]:
        global _WORKER, _STATE
        api_key = str(api_key or "").strip()
        symbol = str(symbol or "").strip()

        if not enabled:
            if _WORKER is not None:
                _WORKER.stop()
                _WORKER = None
            with _LOCK:
                _STATE.enabled = False
                _STATE.connected = False
                _STATE.authenticated = False
                _STATE.auth_status = "idle"
                _STATE.last_event = "disabled"
            return WebSocketLiveEngine.get_status()

        if not api_key or not symbol:
            return WebSocketLiveEngine.get_status()

        key_hash = WebSocketLiveEngine._hash_key(api_key)
        now = _now_ts()
        with _LOCK:
            if _STATE.cooldown_until_ts and now < _STATE.cooldown_until_ts:
                # 連線數達上限時不要在每次 Streamlit rerun 重連，否則會讓 Fugle 繼續拒絕。
                return WebSocketLiveEngine.get_status()

        need_restart = False
        with _LOCK:
            if _WORKER is None:
                need_restart = True
            elif _STATE.symbol != symbol or _STATE.api_key_hash != key_hash:
                need_restart = True
            elif _STATE.last_event in ["closed", "error"] and (_now_ts() - _STATE.last_message_ts > 30):
                # 錯誤後延後重連，避免每次自動刷新都開新連線。
                need_restart = True

        if need_restart:
            if _WORKER is not None:
                _WORKER.stop()
                time.sleep(0.2)
            with _LOCK:
                _STATE = _WSState(api_key_hash=key_hash, symbol=symbol, enabled=True)
            _WORKER = _FugleWSWorker(api_key=api_key, symbol=symbol)
            _WORKER.start()

        return WebSocketLiveEngine.get_status()

    @staticmethod
    def get_status() -> Dict[str, Any]:
        with _LOCK:
            now = _now_ts()
            age = (now - _STATE.last_message_ts) if _STATE.last_message_ts else None
            ch_age = {}
            for ch, t in _STATE.channel_last_message_ts.items():
                ch_age[ch] = round(now - t, 2)
            cooldown_left = 0
            if _STATE.cooldown_until_ts:
                cooldown_left = max(0, int(round(_STATE.cooldown_until_ts - now)))
            return {
                "enabled": _STATE.enabled,
                "symbol": _STATE.symbol,
                "connected": _STATE.connected,
                "authenticated": _STATE.authenticated,
                "auth_status": _STATE.auth_status,
                "last_event": _STATE.last_event,
                "last_error": _STATE.last_error,
                "cooldown_left_sec": cooldown_left,
                "cooldown_reason": _STATE.cooldown_reason,
                "last_message_age_sec": round(age, 2) if age is not None else None,
                "subscribed": dict(_STATE.subscribed),
                "channel_status": dict(_STATE.channel_status),
                "channel_errors": dict(_STATE.channel_errors),
                "channel_age_sec": ch_age,
                "subscribe_requests": dict(_STATE.subscribe_requests),
                "trade_count": len(_STATE.trades),
                "book_count": len(_STATE.books),
                "latest_trade": dict(_STATE.latest_trade),
                "latest_books": dict(_STATE.latest_books),
                "raw_events": list(_STATE.raw_events)[-12:],
                "sent_events": list(_STATE.sent_events)[-12:],
            }

    @staticmethod
    def is_ws_active() -> bool:
        s = WebSocketLiveEngine.get_status()
        channel_status = s.get("channel_status") or {}
        return bool(s.get("authenticated") and any(channel_status.get(ch) == "receiving" for ch in CHANNELS))

    @staticmethod
    def data_source_label() -> str:
        if WebSocketLiveEngine.is_ws_active():
            return "REST + WebSocket 即時流"
        s = WebSocketLiveEngine.get_status()
        if s.get("connected") and s.get("authenticated"):
            return "REST Only（WS 已驗證但未收到頻道資料）"
        if s.get("connected"):
            return "REST Only（WS 等待驗證）"
        return "REST Only"

    @staticmethod
    def apply_to_quote(quote: Dict[str, Any], symbol: str) -> Dict[str, Any]:
        if not isinstance(quote, dict):
            quote = {}
        out = dict(quote)
        with _LOCK:
            lt = dict(_STATE.latest_trade)
            lb = dict(_STATE.latest_books)
            ok_symbol = (not symbol) or (not _STATE.symbol) or str(symbol) == str(_STATE.symbol)
            authenticated = _STATE.authenticated
        if not authenticated or not ok_symbol:
            out["source_detail"] = "REST Only"
            return out

        used_ws = False
        if lt:
            p = _Safe.f(lt.get("price"))
            if p > 0:
                out["price"] = p
                out["last_size"] = _Safe.f(lt.get("size"), out.get("last_size", 0))
                out["trade"] = lt
                out["ws_price"] = p
                out["ws_trade"] = lt
                used_ws = True
        if lb:
            bids = _norm_levels(lb.get("bids"))
            asks = _norm_levels(lb.get("asks"))
            out["bids"] = bids
            out["asks"] = asks
            out["ws_books"] = lb
            used_ws = True
        out["source_detail"] = "REST + WebSocket" if used_ws else "REST Only"
        return out

    @staticmethod
    def get_microstructure(symbol: str = "") -> Dict[str, Any]:
        with _LOCK:
            trades = list(_STATE.trades)
            books = list(_STATE.books)
            latest_trade = dict(_STATE.latest_trade)
            latest_books = dict(_STATE.latest_books)
            status = WebSocketLiveEngine.get_status()

        now = _now_ts()
        recent_trades = [t for t in trades if now - _Safe.f(t.get("_ts"), now) <= 60]
        recent_books = [b for b in books if now - _Safe.f(b.get("_ts"), now) <= 60]

        buy_vol = sum(_Safe.f(t.get("size")) for t in recent_trades if t.get("side") == "BUY")
        sell_vol = sum(_Safe.f(t.get("size")) for t in recent_trades if t.get("side") == "SELL")
        total_vol = buy_vol + sell_vol
        buy_pressure = 50.0 if total_vol <= 0 else 100.0 * buy_vol / total_vol
        sell_pressure = 50.0 if total_vol <= 0 else 100.0 * sell_vol / total_vol

        sizes = [_Safe.f(t.get("size")) for t in recent_trades if _Safe.f(t.get("size")) > 0]
        avg_size = sum(sizes) / len(sizes) if sizes else 0
        large_threshold = max(avg_size * 3.0, 100.0)
        large_buys = [t for t in recent_trades if t.get("side") == "BUY" and _Safe.f(t.get("size")) >= large_threshold]
        large_sells = [t for t in recent_trades if t.get("side") == "SELL" and _Safe.f(t.get("size")) >= large_threshold]

        bid_depth_slope = 0.0
        ask_depth_slope = 0.0
        fake_bid_wall_risk = 0.0
        fake_ask_wall_risk = 0.0
        spread_pct = _Safe.f(latest_books.get("spread_pct"))
        bid_depth = _Safe.f(latest_books.get("bid_depth"))
        ask_depth = _Safe.f(latest_books.get("ask_depth"))
        imbalance = 0.0
        if bid_depth + ask_depth > 0:
            imbalance = (bid_depth - ask_depth) / (bid_depth + ask_depth) * 100

        if len(recent_books) >= 2:
            first = recent_books[0]
            last = recent_books[-1]
            secs = max(_Safe.f(last.get("_ts")) - _Safe.f(first.get("_ts")), 1)
            bid_depth_slope = (_Safe.f(last.get("bid_depth")) - _Safe.f(first.get("bid_depth"))) / secs
            ask_depth_slope = (_Safe.f(last.get("ask_depth")) - _Safe.f(first.get("ask_depth"))) / secs

            for prev, cur in zip(recent_books[:-1], recent_books[1:]):
                prev_bid0 = _Safe.f((prev.get("bids") or [{}])[0].get("size"))
                cur_bid0 = _Safe.f((cur.get("bids") or [{}])[0].get("size"))
                prev_ask0 = _Safe.f((prev.get("asks") or [{}])[0].get("size"))
                cur_ask0 = _Safe.f((cur.get("asks") or [{}])[0].get("size"))
                if prev_bid0 >= max(300, avg_size * 6) and cur_bid0 < prev_bid0 * 0.35:
                    fake_bid_wall_risk = max(fake_bid_wall_risk, min(100, (prev_bid0 - cur_bid0) / max(prev_bid0, 1) * 100))
                if prev_ask0 >= max(300, avg_size * 6) and cur_ask0 < prev_ask0 * 0.35:
                    fake_ask_wall_risk = max(fake_ask_wall_risk, min(100, (prev_ask0 - cur_ask0) / max(prev_ask0, 1) * 100))

        estimated_slippage_pct_buy = min(1.5, max(0.0, spread_pct * 0.5 + (0.12 if ask_depth < 500 and ask_depth > 0 else 0)))
        estimated_slippage_pct_sell = min(1.5, max(0.0, spread_pct * 0.5 + (0.12 if bid_depth < 500 and bid_depth > 0 else 0)))
        effective_cost_add_pct = max(estimated_slippage_pct_buy, estimated_slippage_pct_sell)

        execution_risk = "LOW"
        if spread_pct >= 0.25 or bid_depth + ask_depth < 1200:
            execution_risk = "MEDIUM"
        if spread_pct >= 0.6 or bid_depth + ask_depth < 500:
            execution_risk = "HIGH"

        reasons = []
        if total_vol > 0:
            if buy_pressure >= 62:
                reasons.append(f"WebSocket 主動買量偏強：{buy_pressure:.1f}%")
            elif sell_pressure >= 62:
                reasons.append(f"WebSocket 主動賣量偏強：{sell_pressure:.1f}%")
        if fake_bid_wall_risk >= 60:
            reasons.append("疑似假買牆：買一量快速消失")
        if fake_ask_wall_risk >= 60:
            reasons.append("疑似假賣牆：賣一量快速消失")
        if execution_risk != "LOW":
            reasons.append(f"WebSocket 估計成交風險：{execution_risk}")
        if large_buys:
            reasons.append(f"連續大買偵測：{len(large_buys)} 筆")
        if large_sells:
            reasons.append(f"連續大賣偵測：{len(large_sells)} 筆")

        available = bool(status.get("authenticated") and (recent_trades or recent_books))
        return {
            "available": available,
            "source": "websocket",
            "status": status,
            "buy_pressure": round(buy_pressure, 2),
            "sell_pressure": round(sell_pressure, 2),
            "net_aggressive_flow": round(buy_vol - sell_vol, 2),
            "trade_count_60s": len(recent_trades),
            "large_buy_count_60s": len(large_buys),
            "large_sell_count_60s": len(large_sells),
            "large_order_streak": max(len(large_buys), len(large_sells)),
            "bid_depth": round(bid_depth, 2),
            "ask_depth": round(ask_depth, 2),
            "bid_ask_imbalance": round(imbalance, 2),
            "bid_depth_slope": round(bid_depth_slope, 2),
            "ask_depth_slope": round(ask_depth_slope, 2),
            "fake_bid_wall_risk": round(fake_bid_wall_risk, 2),
            "fake_ask_wall_risk": round(fake_ask_wall_risk, 2),
            "estimated_slippage_pct_buy": round(estimated_slippage_pct_buy, 4),
            "estimated_slippage_pct_sell": round(estimated_slippage_pct_sell, 4),
            "effective_cost_add_pct": round(effective_cost_add_pct, 4),
            "execution_risk": execution_risk,
            "reasons": reasons[:6],
            "latest_trade": latest_trade,
            "latest_books": latest_books,
        }

    @staticmethod
    def render_sidebar_status(st, compact: bool = True):
        status = WebSocketLiveEngine.get_status()
        if not status.get("enabled"):
            st.warning("🟡 WebSocket 未啟用｜目前只用 REST")
            return

        channel_status = status.get("channel_status") or {}
        channel_age = status.get("channel_age_sec") or {}
        channel_errors = status.get("channel_errors") or {}
        any_receiving = any(channel_status.get(ch) == "receiving" for ch in CHANNELS)

        if any_receiving:
            st.success(f"🟢 REST + WebSocket｜{status.get('symbol')}｜最近訊息 {status.get('last_message_age_sec')}s")
        elif status.get("authenticated"):
            st.warning("🟡 REST Only｜WS 已驗證，但頻道尚未收到資料")
        elif status.get("connected"):
            st.info(f"🔵 Socket 已連線｜Auth：{status.get('auth_status')}")
        else:
            st.warning("🟡 REST Only｜WebSocket 尚未連線")

        st.markdown("**連線分層狀態**")
        st.write(f"Socket：{'已連線' if status.get('connected') else '未連線'}")
        st.write(f"Auth：{status.get('auth_status')}")

        st.markdown("**頻道狀態**")
        for ch in CHANNELS:
            s = channel_status.get(ch, "not_sent")
            age = channel_age.get(ch)
            err = channel_errors.get(ch, "")
            age_text = f"｜{age}s 前" if age is not None else ""
            err_text = f"｜{err}" if err else ""
            st.write(f"{ch}：{s}{age_text}{err_text}")

        if status.get("last_error"):
            st.error(f"WS 錯誤：{status.get('last_error')}")
        if status.get("cooldown_left_sec"):
            st.warning(f"重連冷卻：{status.get('cooldown_left_sec')} 秒｜{status.get('cooldown_reason')}")
            st.caption("這通常代表同一組 Fugle API Key 已有其他 WebSocket 連線尚未釋放。請先關閉 WebSocket，等待幾分鐘，或到 Streamlit Cloud Reboot app 後再試。")

        st.markdown("**WS 診斷：送出 / 回傳原始訊息**")

        st.caption("送出的 subscribe payload")
        sub_reqs = status.get("subscribe_requests") or {}
        if sub_reqs:
            for ch, req in sub_reqs.items():
                st.code(_short_json(req, 500), language="json")
        else:
            st.caption("尚未送出 subscribe。")

        st.caption("最近送出的訊息")
        sent = (status.get("sent_events") or [])[-5:]
        if sent:
            for item in sent:
                st.code(_short_json(item.get("payload", item), 700), language="json")
        else:
            st.caption("尚無送出紀錄。")

        st.caption("最近收到的原始訊息")
        raws = (status.get("raw_events") or [])[-10:]
        if raws:
            for item in raws:
                payload = item.get("payload", item)
                st.code(_short_json(payload, 1000), language="json")
        else:
            st.caption("尚未收到 WebSocket 訊息。休市時可能正常，但若 Auth 一直沒回覆就要檢查權限或格式。")

        st.info("判讀：只有 Socket 連線不算成功；Auth 要 success，且 trades/books/candles 至少一個變成 receiving，AI 才真的吃到 WebSocket。")
