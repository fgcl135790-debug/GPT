import streamlit as st
import pandas as pd

from win_rate_engine import WinRateEngine


def _fmt_pct(value):
    try:
        return f"{float(value):.1f}%"
    except Exception:
        return "-"


def render_win_rate_sidebar_panel():
    with st.sidebar.expander("🎯 勝率統計", expanded=False):

        trades = st.session_state.get("winrate_trades", [])
        active = st.session_state.get("winrate_active_trade")

        summary = WinRateEngine.summarize(trades)

        st.caption("記錄真實盤 / 模擬盤 / 回測匯入的訊號結果。")

        if active:
            st.markdown("#### 目前追蹤中")

            st.write(
                f"{active.get('action')}｜"
                f"進場 {active.get('entry_price')}"
            )

            st.write(
                f"停損 {active.get('stop_loss')} "
                f"({active.get('stop_loss_pct')}%)"
            )

            st.write(
                f"停利 {active.get('take_profit')} "
                f"({active.get('take_profit_pct')}%)"
            )

            st.write(
                f"追蹤 {active.get('bars_held', 0)} / "
                f"{active.get('max_hold_bars', 50)} 根K"
            )

        else:
            st.info("目前沒有追蹤中的訊號。")

        st.divider()

        c1, c2 = st.columns(2)

        with c1:
            st.metric("總筆數", summary.get("total", 0))
            st.metric("勝率", _fmt_pct(summary.get("win_rate", 0)))
            st.metric("做多勝率", _fmt_pct(summary.get("buy_win_rate", 0)))

        with c2:
            st.metric("勝 / 敗", f"{summary.get('wins', 0)} / {summary.get('losses', 0)}")
            st.metric("總報酬", _fmt_pct(summary.get("total_pnl", 0)))
            st.metric("做空勝率", _fmt_pct(summary.get("sell_win_rate", 0)))

        reset_clicked = st.button(
            "清空勝率統計",
            use_container_width=True,
            key="winrate_reset",
        )

        if reset_clicked:
            WinRateEngine.reset(st)
            st.success("勝率統計已清空")
            st.rerun()

        if trades:
            st.divider()
            st.caption("最近 10 筆訊號結果")

            df = pd.DataFrame(trades[-10:])

            show_cols = [
                "source",
                "stock_code",
                "action",
                "score",
                "entry_time",
                "entry_price",
                "stop_loss_pct",
                "take_profit_pct",
                "stop_loss",
                "take_profit",
                "exit_time",
                "exit_reason",
                "hold_bars",
                "pnl_pct",
                "result",
            ]

            df = df[[col for col in show_cols if col in df.columns]]

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
                "下載勝率統計 CSV",
                data=csv,
                file_name="winrate_stats.csv",
                mime="text/csv",
                use_container_width=True,
            )
