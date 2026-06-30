import streamlit as st
import pandas as pd

from backtest_engine import BacktestEngine
from win_rate_engine import WinRateEngine


def _fmt_pct(value):
    try:
        return f"{float(value):.1f}%"
    except Exception:
        return "-"


def _fmt_num(value):
    try:
        return f"{float(value):.2f}"
    except Exception:
        return "-"


def render_backtest_sidebar_panel(api_key, stock_code):
    with st.sidebar.expander("📊 回測", expanded=False):

        if not api_key:
            st.warning("請先輸入 Fugle API KEY。")
            return

        # =========================
        # 用 form 包起來，避免 auto refresh 吃掉按鈕狀態
        # =========================

        with st.form(
            key="backtest_form",
            clear_on_submit=False,
        ):
            symbol = st.text_input(
                "回測股票",
                value=str(stock_code),
                key="bt_symbol",
            )

            timeframe = st.selectbox(
                "K 線週期",
                options=["1", "5", "15", "30"],
                index=0,
                format_func=lambda x: f"{x} 分K",
                key="bt_timeframe",
            )

            day_scope_label = st.selectbox(
                "回測範圍",
                options=[
                    "最後一個開市日",
                    "最近 5 個開市日",
                    "近 30 日全部資料",
                ],
                index=2,
                key="bt_day_scope_label",
            )

            day_scope_map = {
                "最後一個開市日": "last_open_day",
                "最近 5 個開市日": "recent_5_days",
                "近 30 日全部資料": "all",
            }

            day_scope = day_scope_map.get(
                day_scope_label,
                "recent_5_days",
            )

            model_mode_label = st.selectbox(
                "AI 判斷模式",
                options=[
                    "專業即時結構 AI（不訓練、不偷看）",
                    "一般 AI 無模型",
                ],
                index=0,
                key="bt_model_mode_label",
            )

            model_mode_map = {
                "專業即時結構 AI（不訓練、不偷看）": "realtime_structure",
                "一般 AI 無模型": "classic",
            }

            model_mode = model_mode_map.get(model_mode_label, "realtime_structure")

            scan_step_bars = st.slider(
                "回測掃描間隔 K 數",
                min_value=1,
                max_value=5,
                value=1,
                step=1,
                key="bt_scan_step_bars",
                help="1 最精準；2~5 比較快但可能跳過部分進場點。",
            )

            # 內部保護用，不顯示在側邊欄。
            max_runtime_seconds = 120

            score_threshold = st.slider(
                "最低 Score",
                min_value=50,
                max_value=95,
                value=60,
                step=5,
                key="bt_score_threshold",
            )

            require_resonance = st.checkbox(
                "只測多週期共振",
                value=False,
                key="bt_require_resonance",
            )

            avoid_open_minutes = st.slider(
                "避開開盤前幾分鐘",
                min_value=0,
                max_value=30,
                value=15,
                step=5,
                key="bt_avoid_open",
            )

            max_hold_bars = st.slider(
                "最多持有 K 數",
                min_value=10,
                max_value=90,
                value=50,
                step=5,
                key="bt_max_hold_bars",
            )

            default_stop_pct = st.slider(
                "回測停損 %",
                min_value=0.2,
                max_value=3.0,
                value=0.7,
                step=0.1,
                key="bt_default_stop_pct",
            )

            default_take_pct = st.slider(
                "回測停利 %",
                min_value=0.3,
                max_value=5.0,
                value=1.8,
                step=0.1,
                key="bt_default_take_pct",
            )

            max_trades_per_day = st.slider(
                "每日最多交易",
                min_value=1,
                max_value=5,
                value=1,
                step=1,
                key="bt_max_trades_per_day",
                help="避免同一段盤整反覆進出，專業當沖通常會限制每日出手次數。",
            )

            loss_cooldown_bars = st.slider(
                "停損後冷卻 K 數",
                min_value=0,
                max_value=80,
                value=30,
                step=5,
                key="bt_loss_cooldown_bars",
                help="剛停損後等待新結構出現，避免同方向連續被洗。",
            )

            stop_after_losses = st.slider(
                "連續虧損幾筆後停手",
                min_value=1,
                max_value=4,
                value=2,
                step=1,
                key="bt_stop_after_losses",
            )

            commission_discount = st.slider(
                "手續費折扣",
                min_value=0.1,
                max_value=1.0,
                value=1.0,
                step=0.1,
                key="bt_commission_discount",
            )

            tax_rate_pct = st.slider(
                "證交稅 %",
                min_value=0.0,
                max_value=0.3,
                value=0.15,
                step=0.01,
                key="bt_tax_rate_pct",
            )

            commission_rate_pct = 0.1425
            effective_commission_pct = commission_rate_pct * commission_discount

            estimated_round_trip_cost = (
                effective_commission_pct
                + effective_commission_pct
                + tax_rate_pct
            )

            if model_mode == "realtime_structure":
                st.caption(
                    f"模式：專業即時結構 AI｜掃描間隔 {scan_step_bars}K｜每日最多 {max_trades_per_day} 筆"
                )
            else:
                st.caption("模式：一般 AI 無模型｜只作對照，不建議當主策略")

            run_clicked = st.form_submit_button(
                "執行回測",
                use_container_width=True,
            )

        # =========================
        # 執行回測
        # =========================

        if run_clicked:
            st.session_state.backtest_status = "running"
            st.session_state.backtest_result = None
            st.session_state.backtest_message = "已收到回測指令，正在抓歷史 K 線..."

            status_box = st.empty()
            progress_box = st.empty()
            progress_bar = st.progress(0)
            status_box.info(st.session_state.backtest_message)

            def _on_backtest_progress(message, percent=None):
                st.session_state.backtest_message = str(message)
                progress_box.info(str(message))
                if percent is not None:
                    try:
                        progress_bar.progress(max(0, min(100, int(percent))))
                    except Exception:
                        pass

            try:
                with st.spinner("回測中，請稍等..."):
                    result = BacktestEngine.run(
                        api_key=api_key,
                        symbol=symbol,
                        timeframe=timeframe,
                        score_threshold=score_threshold,
                        require_resonance=require_resonance,
                        avoid_open_minutes=avoid_open_minutes,
                        max_hold_bars=max_hold_bars,
                        day_scope=day_scope,
                        default_stop_pct=default_stop_pct,
                        default_take_pct=default_take_pct,
                        commission_rate_pct=commission_rate_pct,
                        commission_discount=commission_discount,
                        tax_rate_pct=tax_rate_pct,
                        model_mode=model_mode,
                        scan_step_bars=scan_step_bars,
                        max_runtime_seconds=max_runtime_seconds,
                        max_trades_per_day=max_trades_per_day,
                        loss_cooldown_bars=loss_cooldown_bars,
                        stop_after_losses=stop_after_losses,
                        progress_callback=_on_backtest_progress,
                    )

                st.session_state.backtest_result = result
                st.session_state.backtest_status = "done"

                if result.get("ok"):
                    st.session_state.backtest_message = result.get(
                        "message",
                        "回測完成",
                    )
                    status_box.success(st.session_state.backtest_message)
                else:
                    st.session_state.backtest_message = result.get(
                        "message",
                        "回測失敗",
                    )
                    status_box.error(st.session_state.backtest_message)

            except Exception as e:
                st.session_state.backtest_status = "error"
                st.session_state.backtest_result = {
                    "ok": False,
                    "message": str(e),
                    "summary": {},
                    "trades": [],
                }
                st.session_state.backtest_message = str(e)

                status_box.error("回測執行時發生錯誤")
                st.exception(e)

        # =========================
        # 顯示狀態
        # =========================

        result = st.session_state.get("backtest_result")

        if not result:
            st.info("尚未執行回測。")
            return

        if not result.get("ok"):
            st.error(result.get("message", "回測失敗"))
            return

        summary = result.get("summary", {})
        trades = result.get("trades", [])
        selected_days = result.get("selected_days", [])

        st.divider()

        st.caption(
            f"{result.get('symbol')}｜{result.get('timeframe')}分K｜"
            f"回測 {result.get('days')} 日｜來源 {result.get('all_days')} 日｜"
            f"{result.get('candles')} 根K｜"
            f"用時 {result.get('elapsed_seconds', '-')} 秒｜"
            f"掃描間隔 {result.get('scan_step_bars', 1)}K"
        )

        leak_warning = result.get("leak_warning")
        if leak_warning:
            if result.get("model_mode") == "same_period":
                st.warning(leak_warning)
            else:
                st.info(leak_warning)

        skipped_days = result.get("skipped_days", []) or []
        if skipped_days:
            st.caption(
                "略過日期：" + "、".join(
                    [f"{x.get('date')}({x.get('reason')})" for x in skipped_days[-5:]]
                )
            )

        if selected_days:
            st.info(
                "回測日期：" + "、".join(selected_days[-5:])
            )

        c1, c2 = st.columns(2)

        with c1:
            st.metric("總交易", summary.get("total", 0))
            st.metric("勝率", _fmt_pct(summary.get("win_rate", 0)))
            st.metric("做多勝率", _fmt_pct(summary.get("buy_win_rate", 0)))

        with c2:
            st.metric("Profit Factor", _fmt_num(summary.get("profit_factor", 0)))
            st.metric("總報酬", _fmt_pct(summary.get("total_pnl", 0)))
            st.metric("做空勝率", _fmt_pct(summary.get("sell_win_rate", 0)))

        st.caption(
            f"最大回撤 {_fmt_pct(summary.get('max_drawdown', 0))}｜"
            f"最大連敗 {summary.get('max_consecutive_loss', 0)}"
        )

        if "gross_total_pnl" in summary or "total_cost_pct" in summary:
            st.divider()
            st.caption("損益拆解")

            c3, c4 = st.columns(2)

            with c3:
                st.metric(
                    "未扣成本",
                    _fmt_pct(summary.get("gross_total_pnl", 0)),
                )

                st.metric(
                    "成本合計",
                    _fmt_pct(summary.get("total_cost_pct", 0)),
                )

            with c4:
                st.metric(
                    "扣成本後",
                    _fmt_pct(summary.get("net_total_pnl", summary.get("total_pnl", 0))),
                )

                st.metric(
                    "平均每筆",
                    _fmt_pct(summary.get("avg_pnl", 0)),
                )

        if not trades:
            st.warning(
                "這次沒有符合條件的交易。系統不會用候選單或事後結果硬湊交易；"
                "若使用即時結構 AI 仍過少，請先降低最低 Score 或檢查 Fugle 歷史 K 是否只有部分交易日。"
            )
            return

        import_clicked = st.button(
            "匯入勝率統計",
            use_container_width=True,
            key="bt_import_to_winrate",
        )

        if import_clicked:
            count = WinRateEngine.import_backtest_trades(
                st=st,
                trades=trades,
            )

            st.success(f"已匯入 {count} 筆回測交易到勝率統計")

        st.divider()
        st.caption("最近 10 筆回測交易")

        df = pd.DataFrame(trades[-10:])

        show_cols = [
            "date",
            "action",
            "score",
            "entry_time",
            "entry_price",
            "stop_loss_pct",
            "take_profit_pct",
            "stop_loss",
            "take_profit",
            "exit_time",
            "exit_price",
            "exit_reason",
            "hold_bars",
            "gross_pnl_pct",
            "cost_pct",
            "pnl_pct",
            "predicted_win_rate",
            "predicted_expected_value",
            "required_win_rate",
            "estimated_mfe_pct",
            "estimated_mae_pct",
            "mfe_mae_ratio",
            "ev_after_quality",
            "best_favorable_pct",
            "setup_type",
            "raw_win_rate",
            "calibrated_win_rate",
            "filter_penalty",
            "professional_filters",
            "hard_fail_reasons",
            "model_train_start",
            "model_train_end",
            "result",
        ]

        df = df[
            [
                col
                for col in show_cols
                if col in df.columns
            ]
        ]

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            height=230,
        )

        csv = pd.DataFrame(trades).to_csv(
            index=False,
            encoding="utf-8-sig",
        )

        st.download_button(
            "下載回測明細 CSV",
            data=csv,
            file_name=f"backtest_{symbol}_{timeframe}m.csv",
            mime="text/csv",
            use_container_width=True,
        )
