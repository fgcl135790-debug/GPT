import streamlit as st

# =========================
# Page Config 必須盡量放最前面
# =========================

st.set_page_config(
    page_title="主力監控",
    layout="wide",
    page_icon="🏦",
)


# =========================
# Dashboard CSS
# =========================

st.markdown(
    """
<style>
html, body, [data-testid="stAppViewContainer"] {
    background: #080c13;
}

/* Streamlit 上方列 */
header[data-testid="stHeader"] {
    background: #080c13;
    height: 38px;
}

/* 主內容寬度 */
.block-container {
    max-width: 1840px;
    padding: 2.05rem 0.55rem 0.6rem 0.55rem !important;
}

/* 壓縮標題 */
h1, h2, h3 {
    font-size: 14px !important;
    margin-top: 0 !important;
    margin-bottom: 0.16rem !important;
}

/* 全域字體 */
p, div, span {
    font-size: 12px;
}

/* 壓縮垂直間距 */
div[data-testid="stVerticalBlock"] {
    gap: 0.20rem;
}

/* 壓縮左右欄位間距 */
div[data-testid="stHorizontalBlock"] {
    gap: 0.40rem;
}

/* 分隔線 */
hr {
    margin: 0.16rem 0 !important;
    border-color: rgba(255,255,255,0.07) !important;
}

/* 側邊欄 */
[data-testid="stSidebar"] {
    background: #0b111c;
}

/* 按鈕 */
button[kind="secondary"] {
    height: 28px;
    padding: 2px 8px;
}

/* Plotly 工具列縮小 */
.modebar {
    transform: scale(0.78);
    transform-origin: top right;
}

/* 表格 */
.stDataFrame {
    font-size: 11.5px;
}

/* Expander 壓縮 */
[data-testid="stExpander"] {
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 10px;
    background: rgba(255,255,255,0.025);
}

[data-testid="stExpander"] details {
    padding: 0;
}

/* 隱藏 footer */
footer {
    visibility: hidden;
}

/* 手機版 */
@media (max-width: 900px) {
    .block-container {
        padding: 2.0rem 0.45rem 0.6rem 0.45rem !important;
    }

    h1, h2, h3 {
        font-size: 13px !important;
    }
}


/* =========================
   手機響應式修正
   ========================= */
* { box-sizing: border-box; }
html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
    overflow-x: hidden !important;
    max-width: 100vw !important;
}
[data-testid="stHorizontalBlock"], [data-testid="column"] { min-width: 0 !important; }
.stPlotlyChart, .js-plotly-plot, .plot-container { max-width: 100% !important; }

@media (max-width: 760px) {
    .block-container {
        max-width: 100vw !important;
        width: 100vw !important;
        padding: 0.75rem 0.45rem 5.0rem 0.45rem !important;
    }
    header[data-testid="stHeader"] { height: 30px !important; }
    div[data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
        gap: 0.45rem !important;
        width: 100% !important;
    }
    div[data-testid="column"] {
        flex: 1 1 100% !important;
        width: 100% !important;
        max-width: 100% !important;
        min-width: 0 !important;
    }
    div[role="radiogroup"], div[data-baseweb="radio"] {
        flex-wrap: wrap !important;
        max-width: 100% !important;
    }
    button, div[data-testid="stButton"] button {
        min-height: 34px !important;
        white-space: nowrap !important;
    }
    .modebar {
        transform: scale(0.72) !important;
        transform-origin: top right !important;
    }
    .stDataFrame, [data-testid="stDataFrame"] {
        max-width: 100% !important;
        overflow-x: auto !important;
    }
    p, div, span { font-size: 12px; }
}

</style>
""",
    unsafe_allow_html=True,
)


# =========================
# Import 區：任何 import 錯誤都會顯示
# =========================

try:
    import random
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from market_analyzer import MarketAnalyzer
    from ai_predictor import AIPredictor
    from decision_engine import DecisionEngine
    from multi_period_engine import MultiPeriodEngine
    from big_order_engine import BigOrderEngine
    from trade_alert_engine import TradeAlertEngine
    from alert_engine import AlertEngine
    from market_flow_engine import MarketFlowEngine
    from win_rate_engine import WinRateEngine

    # 當沖模型是加值功能：缺檔時不讓主畫面整個掛掉
    try:
        from stock_model_cache import StockModelCache
    except Exception:
        StockModelCache = None

    from rest_microstructure_engine import RestMicrostructureEngine
    from websocket_live_engine import WebSocketLiveEngine

    from ui.header import render_header
    from ui.chart_panel import render_chart
    from ui.lower_market_grid import render_lower_market_grid
    from ui.decision_card import render_decision_card
    from ui.rebound_panel import render_rebound_panel
    from ui.main_force_panel import render_main_force_panel
    from ui.alerts import render_alerts
    from ui.sidebar import render_sidebar
    from ui.backtest_sidebar import render_backtest_sidebar_panel
    from ui.win_rate_sidebar import render_win_rate_sidebar_panel
    from ui.event_stream_panel import render_event_stream_panel
    from ui.kline_export_sidebar import render_kline_export_sidebar_panel

    from core.data_engine import get_market_data
    from streamlit_autorefresh import st_autorefresh

except Exception as e:
    st.error("程式在 import 階段就中斷，所以畫面才會空白。")
    st.exception(e)
    st.stop()


# =========================
# 小工具
# =========================

def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def _resolve_api_key(api_key):
    """
    統一從 sidebar 回傳值與 session_state 讀取 Fugle API Key。
    這可以避免畫面上有密碼點點，但主程式拿到空值的問題。
    """
    return (
        api_key
        or st.session_state.get("runtime_fugle_api_key")
        or st.session_state.get("fugle_api_key")
        or ""
    ).strip()


def _get_loaded_model_package(stock_code):
    """
    只讀取已建立的模型，不自動抓 30 天 K 線。
    避免 Streamlit 每次刷新時卡住主畫面。
    """
    package = st.session_state.get("current_intraday_model_package")

    if not package:
        return None

    if str(package.get("symbol", "")) != str(stock_code):
        return None

    return package


def _render_intraday_model_sidebar(api_key, stock_code, data_source):
    """
    當沖模型改成手動建立。
    主畫面行情先能穩定運作，使用者需要模型時再按鈕建立。
    """
    with st.sidebar.expander("🧠 當沖模型", expanded=False):
        if StockModelCache is None:
            st.warning("stock_model_cache.py 尚未載入，暫時無法建立模型。")
            return

        if data_source != "真實盤":
            st.info("當沖模型只在真實盤使用。")
            return

        if not api_key:
            st.warning("請先輸入 Fugle API KEY。")
            return

        package = _get_loaded_model_package(stock_code)

        if package:
            st.success("模型已建立")
            st.caption(f"股票：{package.get('symbol')}")
            st.caption(
                f"區間：{package.get('start_date')} ~ "
                f"{package.get('end_date')}"
            )
            st.caption(f"交易日：{package.get('trading_days')}")
            st.caption(f"K線：{package.get('kline_rows')} 根")
            st.caption(f"候選標籤：{package.get('label_rows')} 筆")
            st.caption(f"BUY 全樣本勝率：{package.get('buy_win_rate_all')}%")
            st.caption(f"SELL 全樣本勝率：{package.get('sell_win_rate_all')}%")
        else:
            st.info("尚未建立目前股票模型。主畫面會先用一般 AI 監控。")

        build_clicked = st.button(
            "建立 / 重建目前股票模型",
            use_container_width=True,
            key="build_intraday_model",
        )

        if build_clicked:
            try:
                with st.spinner("正在抓取近 30 日 K 線並建立模型..."):
                    StockModelCache.clear_symbol(st, stock_code)
                    package = StockModelCache.get_or_build(
                        st=st,
                        api_key=api_key,
                        symbol=stock_code,
                        timeframe="1",
                        stop_pct=0.7,
                        take_pct=1.8,
                        max_hold_bars=50,
                        cost_pct=0.435,
                        force_rebuild=True,
                    )

                    st.session_state.current_intraday_model_package = package

                st.success("模型建立完成")
                st.rerun()

            except Exception as e:
                st.error("模型建立失敗")
                st.exception(e)


def reset_state():
    MarketFlowEngine.reset_market_state(st)
    try:
        RestMicrostructureEngine.reset(st)
    except Exception:
        pass
    try:
        WebSocketLiveEngine.reset(st)
    except Exception:
        pass

    # 手動重置時，下一次會重新建立模擬路徑
    st.session_state.market_context_key = None
    st.session_state.sim_run_id = random.randint(100000, 999999)


def init_session_state():
    MarketFlowEngine.init_session_state(st)
    try:
        RestMicrostructureEngine.init_state(st)
    except Exception:
        pass


# =========================
# 主程式
# =========================

def main():

    init_session_state()
    WinRateEngine.init_session_state(st)

    if "market_context_key" not in st.session_state:
        st.session_state.market_context_key = None

    if "sim_run_id" not in st.session_state:
        st.session_state.sim_run_id = random.randint(100000, 999999)

    now = datetime.now(ZoneInfo("Asia/Taipei"))

    # =========================
    # Sidebar
    # =========================

    (
        stock_code,
        data_source,
        api_key,
        mode,
        refresh_sec,
        mobile_layout,
        websocket_enabled,
    ) = render_sidebar(reset_state)

    api_key = _resolve_api_key(api_key)

    st.sidebar.caption(
        f"主程式 API KEY：已讀取，長度 {len(api_key)}"
        if api_key
        else "主程式 API KEY：未讀取"
    )

    # =========================
    # Sidebar：實戰功能 + 診斷
    # =========================

    with st.sidebar.expander("📡 WebSocket 診斷", expanded=True):
        if data_source == "真實盤" and websocket_enabled and api_key:
            WebSocketLiveEngine.ensure_running(
                api_key=api_key,
                symbol=stock_code,
                enabled=True,
            )
        else:
            WebSocketLiveEngine.ensure_running(
                api_key=api_key,
                symbol=stock_code,
                enabled=False,
            )
        WebSocketLiveEngine.render_sidebar_status(st)

    # 這三個功能先恢復：回測、勝率統計、真實 K 線匯出。
    # WebSocket 診斷保留，方便確認 AI 是否真的吃到 trades/books/candles。
    render_backtest_sidebar_panel(
        api_key=api_key,
        stock_code=stock_code,
    )

    render_win_rate_sidebar_panel()

    render_kline_export_sidebar_panel(
        api_key=api_key,
        stock_code=stock_code,
    )

    # 當沖模型仍維持手動建立，避免每次刷新抓 30 日 K 線卡住主畫面。
    _render_intraday_model_sidebar(
        api_key=api_key,
        stock_code=stock_code,
        data_source=data_source,
    )

    # =========================
    # 切換股票 / 資料來源 / 模擬模式時清空
    # =========================

    context_key = f"{stock_code}|{data_source}|{mode}"
    old_context_key = st.session_state.get("market_context_key")

    if old_context_key != context_key:
        MarketFlowEngine.reset_market_state(
            st=st,
            keep_stock=stock_code,
        )

        st.session_state.market_context_key = context_key

        # 只有切換情境 / 股票 / 資料來源時，才重新產生模擬走勢
        # 不能每次 refresh 都 random
        if data_source == "模擬盤":
            st.session_state.sim_run_id = random.randint(100000, 999999)

        WinRateEngine.reset(st)
        try:
            RestMicrostructureEngine.reset(st)
        except Exception:
            pass
        try:
            WebSocketLiveEngine.reset(st)
        except Exception:
            pass

    # =========================
    # Auto Refresh
    # =========================

    chart_fullscreen = st.session_state.get("chart_fullscreen", False)
    backtest_running = st.session_state.get("backtest_status") == "running"

    if not chart_fullscreen and not backtest_running:
        st_autorefresh(
            interval=refresh_sec * 1000,
            key="v75_dashboard_refresh",
        )
    elif chart_fullscreen:
        st.info("圖表全屏檢視中，自動刷新已暫停。按圖表工具列的「返回」恢復。")
    elif backtest_running:
        st.info("回測執行中，自動刷新已暫停。")

    # =========================
    # 取得資料
    # =========================

    api_key = _resolve_api_key(api_key)

    if data_source == "真實盤" and not api_key:
        st.warning("請輸入 API KEY，或先切換到模擬盤測試 UI。")
        st.stop()

    try:
        with st.spinner("取得行情資料中..."):
            quote = get_market_data(
                data_source=data_source,
                api_key=api_key,
                stock_code=stock_code,
                tick=st.session_state.tick,
                mode=mode,
                sim_run_id=st.session_state.get("sim_run_id", 0),
            )

        if not quote:
            raise ValueError("empty quote")

        if data_source == "真實盤" and websocket_enabled and api_key:
            WebSocketLiveEngine.ensure_running(
                api_key=api_key,
                symbol=stock_code,
                enabled=True,
            )
            quote = WebSocketLiveEngine.apply_to_quote(quote, stock_code)

        st.session_state.last_good_quote = quote
        st.session_state.api_error_message = None

    except Exception as e:
        st.session_state.api_error_message = type(e).__name__

        if st.session_state.last_good_quote is not None:
            quote = st.session_state.last_good_quote

            st.warning(
                f"資料來源暫時異常，已使用上一筆有效資料。錯誤：{type(e).__name__}"
            )

        else:
            st.error("Fugle API 暫時異常，且目前沒有上一筆有效資料可使用。")
            st.exception(e)
            st.stop()

    # 模擬盤才每次刷新推進 tick
    if data_source == "模擬盤":
        st.session_state.tick += 1

    # =========================
    # 統一資料流 Snapshot
    # 真實盤休市後，serial 不會再用現在時間，所以不會一直新增假資料
    # =========================

    snapshot = MarketFlowEngine.build_snapshot(
        st=st,
        quote=quote,
        stock_code=stock_code,
        now=now,
        data_source=data_source,
    )

    name = snapshot["name"]
    price = snapshot["price"]
    vwap = snapshot["vwap"]
    volume = snapshot["volume"]
    high = snapshot["high"]
    low = snapshot["low"]
    bids = snapshot["bids"]
    asks = snapshot["asks"]
    serial = snapshot["serial"]
    market_status = snapshot.get("market_status", "未知")

    prices = snapshot["prices"]
    volumes = snapshot["volumes"]
    vwaps = snapshot["vwaps"]
    times = snapshot["times"]

    # =========================
    # REST / WebSocket 微結構：五檔序列 / 逐筆成交 / 假牆 / 滑價估算
    # =========================

    rest_microstructure = RestMicrostructureEngine.update(
        st=st,
        stock_code=stock_code,
        serial=serial,
        price=price,
        bids=bids,
        asks=asks,
        volume=volume,
        now=now,
    )

    websocket_microstructure = WebSocketLiveEngine.get_microstructure(stock_code)

    # WebSocket 有資料時，以 WebSocket 逐筆成交 / 連續五檔為主；
    # REST 快照序列保留當備援。
    if websocket_microstructure.get("available"):
        combined_microstructure = dict(rest_microstructure or {})
        combined_microstructure.update(websocket_microstructure)
        combined_microstructure["fallback_rest_microstructure"] = rest_microstructure
    else:
        combined_microstructure = rest_microstructure

    # =========================
    # 主力大單偵測
    # =========================

    if st.session_state.big_order_last_serial != serial:
        st.session_state.big_order_last_serial = serial

        big_order = BigOrderEngine.detect(
            stock_code=stock_code,
            name=name,
            price=price,
            volume=volume,
            bids=bids,
            asks=asks,
            prices=prices,
            volumes=volumes,
        )

        if big_order is not None:
            st.session_state.big_order_log.append(big_order)

            if len(st.session_state.big_order_log) > 100:
                st.session_state.big_order_log = st.session_state.big_order_log[-100:]

    # =========================
    # 技術指標
    # =========================

    ema5 = MarketAnalyzer.calculate_ema(prices, 5)
    ema20 = MarketAnalyzer.calculate_ema(prices, 20)
    ema60 = MarketAnalyzer.calculate_ema(prices, 60)

    rsi = MarketAnalyzer.calculate_rsi(prices)
    macd, macd_signal, _ = MarketAnalyzer.calculate_macd(prices)

    momentum = MarketAnalyzer.momentum(prices)

    # =========================
    # 五檔買賣力道
    # =========================

    bid_total = sum(
        [
            _safe_float(b.get("size", 0))
            for b in bids
        ]
    )

    ask_total = sum(
        [
            _safe_float(a.get("size", 0))
            for a in asks
        ]
    )

    bid_ratio = bid_total / max(ask_total, 1)

    # =========================
    # AI Predict
    # =========================

    ai = AIPredictor.predict_trade(
        prices,
        volumes,
        ema5,
        ema20,
        ema60,
        rsi,
        macd,
        macd_signal,
        momentum,
        bid_ratio=bid_ratio,
        vwap=vwap,
    )

    signal = ai.get("signal", "WAIT")
    score = ai.get("score", 0)
    risk = ai.get("risk", "監控中")
    state = ai.get("market_state", "資料累積中")
    rebound = ai.get("rebound_prob", 0)

    # 當沖模型只使用「已手動建立」的模型，不在每次刷新時自動抓 30 日 K 線。
    intraday_model_package = _get_loaded_model_package(stock_code)

    if intraday_model_package is not None:
        ai["intraday_model_package"] = intraday_model_package

    # =========================
    # Decision Engine
    # =========================

    decision = DecisionEngine.generate(
        ai=ai,
        price=price,
        vwap=vwap,
        ema5=ema5,
        ema20=ema20,
        ema60=ema60,
        rsi=rsi,
        macd=macd,
        macd_signal=macd_signal,
        bid_ratio=bid_ratio,
        prices=prices,
        volumes=volumes,
        vwap_values=vwaps,
        time_values=times,
        bids=bids,
        asks=asks,
        rest_microstructure=combined_microstructure,
    )

    # =========================
    # Multi Period Engine
    # =========================

    multi_period = MultiPeriodEngine.analyze(
        prices=prices,
        volumes=volumes,
        vwap_values=vwaps,
        time_values=times,
    )

    # 成本感知模型訊號以「扣成本後正期望」為主，
    # 多週期只當參考，不再直接把正期望模型訊號改成 WAIT。
    model_signal_active = (
        decision.get("action") in ["BUY", "SELL"]
        and decision.get("model_label_rows", 0)
    )

    if model_signal_active:
        decision["multi_period"] = multi_period
        decision["multi_period_reference_status"] = multi_period.get("status", "")
        reasons = list(decision.get("reasons", []))
        reasons.insert(0, f"多週期參考：{multi_period.get('status', '未知')}｜模型仍以扣成本期望為主")
        decision["reasons"] = reasons[:8]
    else:
        decision = MultiPeriodEngine.apply_to_decision(
            decision=decision,
            multi_period=multi_period,
        )

    # =========================
    # Header 同步最終決策結果
    # =========================

    final_action = decision.get("action", "WAIT")
    final_score = decision.get("score", score)
    final_rebound = decision.get("rebound", rebound)
    final_state = decision.get("multi_period_status", state)

    score = final_score
    signal = final_action
    rebound = final_rebound

    if final_action == "BUY":
        state = f"多方監控｜{final_state}"

    elif final_action == "SELL":
        state = f"空方監控｜{final_state}"

    else:
        state = f"等待確認｜{final_state}"

    # 休市時，Header 狀態補上休市提醒，但不影響決策卡內容
    if data_source == "真實盤" and market_status == "休市":
        state = f"休市｜{state}"

    if score >= 80:
        risk = "方向明確"

    elif score >= 65:
        risk = "可觀察"

    elif score <= 40:
        risk = "高風險"

    else:
        risk = "等待確認"

    # =========================
    # Trade Alert
    # =========================

    trade_alert = TradeAlertEngine.track(
        decision=decision,
        price=price,
    )

    WinRateEngine.update_live(
        st=st,
        stock_code=stock_code,
        name=name,
        data_source=data_source,
        price=price,
        decision=decision,
        now=now,
        min_score=75,
        max_hold_bars=50,
    )

    # =========================
    # Alert Engine
    # =========================

    alerts = AlertEngine.build(
        decision=decision,
        trade_alert=trade_alert,
        big_order_log=st.session_state.big_order_log,
    )

    # =========================
    # Header
    # =========================

    ws_status = {}
    try:
        ws_status = WebSocketLiveEngine.get_status() or {}
    except Exception:
        ws_status = {}

    if st.session_state.get("api_error_message"):
        connection_status = "資料延遲"
    elif data_source == "真實盤" and websocket_enabled and WebSocketLiveEngine.is_ws_active():
        connection_status = "REST + WS"
    elif data_source == "真實盤" and market_status == "休市":
        connection_status = "休市快照"
    elif data_source == "真實盤":
        connection_status = "REST"
    else:
        connection_status = "模擬盤"

    render_header(
        name=name,
        stock_code=stock_code,
        price=price,
        score=score,
        rebound=rebound,
        risk=risk,
        state=state,
        signal=signal,
        bid_ratio=bid_ratio,
        now=now,
        connection_status=connection_status,
        data_source=data_source,
    )

    # =========================
    # 全屏圖表模式
    # =========================

    if st.session_state.get("chart_fullscreen", False):
        render_chart(
            prices=prices,
            volumes=volumes,
            vwap_values=vwaps,
            time_values=times,
            decision=decision,
            trade_alert=trade_alert,
        )
        return

    # =========================
    # V7.6 Dashboard Layout
    # =========================

    if mobile_layout:
        # =========================
        # 手機版：單欄順序，避免左右欄位把畫面撐寬
        # =========================

        render_decision_card(decision)

        render_chart(
            prices=prices,
            volumes=volumes,
            vwap_values=vwaps,
            time_values=times,
            decision=decision,
            trade_alert=trade_alert,
        )

        render_lower_market_grid(
            bids=bids,
            asks=asks,
            decision=decision,
            price=price,
            vwap=vwap,
            ema5=ema5,
            ema20=ema20,
            rsi=rsi,
            macd=macd,
            macd_signal=macd_signal,
            volume=volume,
            volumes=volumes,
        )

        render_rebound_panel(
            decision=decision,
            trade_alert=trade_alert,
        )

        render_main_force_panel(
            bids=bids,
            asks=asks,
            big_order_log=st.session_state.big_order_log,
            decision=decision,
        )

        render_alerts(alerts)

        render_event_stream_panel(
            big_order_log=st.session_state.big_order_log,
            decision=decision,
        )

    else:
        main_left, main_right = st.columns(
            [1.92, 0.92],
            gap="small",
        )

        # =========================
        # 左側：主圖 + 市場資訊 + 大單事件流
        # =========================

        with main_left:
            render_chart(
                prices=prices,
                volumes=volumes,
                vwap_values=vwaps,
                time_values=times,
                decision=decision,
                trade_alert=trade_alert,
            )

            render_lower_market_grid(
                bids=bids,
                asks=asks,
                decision=decision,
                price=price,
                vwap=vwap,
                ema5=ema5,
                ema20=ema20,
                rsi=rsi,
                macd=macd,
                macd_signal=macd_signal,
                volume=volume,
                volumes=volumes,
            )

            render_event_stream_panel(
                big_order_log=st.session_state.big_order_log,
                decision=decision,
            )

        # =========================
        # 右側：決策 + 反彈 + 主力 + 警示
        # =========================

        with main_right:
            render_decision_card(decision)

            render_rebound_panel(
                decision=decision,
                trade_alert=trade_alert,
            )

            render_main_force_panel(
                bids=bids,
                asks=asks,
                big_order_log=st.session_state.big_order_log,
                decision=decision,
            )

            render_alerts(alerts)


# =========================
# Run
# =========================

try:
    main()

except Exception as e:
    st.error("程式執行途中發生錯誤，所以剛剛才會整頁空白。")
    st.exception(e)
