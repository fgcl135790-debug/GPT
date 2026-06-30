import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

from ui.multi_period_panel import render_multi_period_analysis
from ui.theme import (
    UP_COLOR,
    DOWN_COLOR,
    WAIT_COLOR,
    TEXT,
    SUBTEXT,
    CARD_BG,
    CARD_BORDER,
)

from ui.html_utils import render_html


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def _safe_int(value, default=0):
    try:
        return int(round(float(value)))
    except Exception:
        return default


def _ema(values, span):
    nums = [_safe_float(v) for v in values]

    if not nums:
        return []

    alpha = 2 / (span + 1)
    result = [nums[0]]

    for v in nums[1:]:
        result.append(alpha * v + (1 - alpha) * result[-1])

    return result


def _macd(values):
    nums = [_safe_float(v) for v in values]

    if not nums:
        return [], [], []

    ema12 = _ema(nums, 12)
    ema26 = _ema(nums, 26)

    macd_line = []

    for i in range(len(nums)):
        macd_line.append(ema12[i] - ema26[i])

    signal_line = _ema(macd_line, 9)

    hist = []

    for i in range(len(nums)):
        hist.append(macd_line[i] - signal_line[i])

    return macd_line, signal_line, hist


def _to_lot(volume):
    volume = _safe_float(volume)

    if volume >= 1000:
        return round(volume / 1000, 2)

    return round(volume, 2)


def _to_datetime(value):
    if isinstance(value, datetime):
        return value

    try:
        return datetime.fromisoformat(str(value))
    except Exception:
        return None


def _period_minutes(period):
    mapping = {
        "1分": 1,
        "5分": 5,
        "15分": 15,
        "30分": 30,
        "日": 390,
    }

    return mapping.get(period, 1)


def _bucket_time(dt, minutes):
    if dt is None:
        return None

    if minutes >= 390:
        return dt.replace(
            hour=9,
            minute=0,
            second=0,
            microsecond=0,
        )

    minute = (dt.minute // minutes) * minutes

    return dt.replace(
        minute=minute,
        second=0,
        microsecond=0,
    )


def _prepare_ticks(prices, volumes, vwaps, times):
    clean = []

    prices = prices or []
    volumes = volumes or []
    vwaps = vwaps or []
    times = times or []

    for i, price in enumerate(prices):
        p = _safe_float(price)

        if p <= 0:
            continue

        v = _safe_float(volumes[i]) if i < len(volumes) else 0
        w = _safe_float(vwaps[i]) if i < len(vwaps) else p
        t = _to_datetime(times[i]) if i < len(times) else None

        if w <= 0:
            w = p

        clean.append(
            {
                "price": p,
                "volume": v,
                "vwap": w,
                "time": t,
            }
        )

    return clean


def _aggregate_line(prices, volumes, vwaps, times, period):
    clean = _prepare_ticks(prices, volumes, vwaps, times)

    if not clean:
        return [], [], [], []

    if period in ["1分", "日"]:
        agg_prices = [item["price"] for item in clean]
        agg_volumes = [item["volume"] for item in clean]
        agg_vwaps = [item["vwap"] for item in clean]
        labels = []

        for idx, item in enumerate(clean):
            if item["time"] is not None:
                labels.append(item["time"])
            else:
                labels.append(f"T{idx + 1}")

        return agg_prices, agg_volumes, agg_vwaps, labels

    minutes = _period_minutes(period)
    buckets = {}
    bucket_order = []
    fallback_index = 0

    for item in clean:
        key = _bucket_time(item["time"], minutes)

        if key is None:
            key = f"T{fallback_index + 1}"
            fallback_index += 1

        if key not in buckets:
            buckets[key] = {
                "prices": [],
                "volumes": [],
                "vwaps": [],
                "label": key,
            }
            bucket_order.append(key)

        buckets[key]["prices"].append(item["price"])
        buckets[key]["volumes"].append(item["volume"])
        buckets[key]["vwaps"].append(item["vwap"])

    agg_prices = []
    agg_volumes = []
    agg_vwaps = []
    labels = []

    for key in bucket_order:
        group = buckets[key]

        if not group["prices"]:
            continue

        agg_prices.append(group["prices"][-1])
        agg_volumes.append(sum(group["volumes"]))

        valid_vwaps = [
            _safe_float(v)
            for v in group["vwaps"]
            if _safe_float(v) > 0
        ]

        if valid_vwaps:
            agg_vwaps.append(sum(valid_vwaps) / len(valid_vwaps))
        else:
            agg_vwaps.append(group["prices"][-1])

        labels.append(group["label"])

    return agg_prices, agg_volumes, agg_vwaps, labels


def _aggregate_ohlc(prices, volumes, vwaps, times, period):
    clean = _prepare_ticks(prices, volumes, vwaps, times)

    if not clean:
        return {
            "x": [],
            "open": [],
            "high": [],
            "low": [],
            "close": [],
            "volume": [],
            "vwap": [],
        }

    minutes = _period_minutes(period)
    buckets = {}
    bucket_order = []
    fallback_index = 0

    for item in clean:
        key = _bucket_time(item["time"], minutes)

        if key is None:
            key = f"T{fallback_index + 1}"
            fallback_index += 1

        if key not in buckets:
            buckets[key] = {
                "prices": [],
                "volumes": [],
                "vwaps": [],
                "label": key,
            }
            bucket_order.append(key)

        buckets[key]["prices"].append(item["price"])
        buckets[key]["volumes"].append(item["volume"])
        buckets[key]["vwaps"].append(item["vwap"])

    x = []
    opens = []
    highs = []
    lows = []
    closes = []
    vols = []
    k_vwaps = []

    for key in bucket_order:
        group = buckets[key]
        ps = group["prices"]

        if not ps:
            continue

        opens.append(ps[0])
        highs.append(max(ps))
        lows.append(min(ps))
        closes.append(ps[-1])
        vols.append(sum(group["volumes"]))

        valid_vwaps = [
            _safe_float(v)
            for v in group["vwaps"]
            if _safe_float(v) > 0
        ]

        if valid_vwaps:
            k_vwaps.append(sum(valid_vwaps) / len(valid_vwaps))
        else:
            k_vwaps.append(ps[-1])

        x.append(group["label"])

    return {
        "x": x,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": vols,
        "vwap": k_vwaps,
    }


def _select_control(label, options, default, key):
    if st.session_state.get("mobile_layout", False):
        return st.selectbox(
            label,
            options,
            index=options.index(default),
            key=key,
            label_visibility="collapsed",
        )

    if hasattr(st, "segmented_control"):
        try:
            value = st.segmented_control(
                label,
                options,
                default=default,
                key=key,
                label_visibility="collapsed",
            )

            if value is None:
                return default

            return value

        except TypeError:
            pass

    return st.radio(
        label,
        options,
        index=options.index(default),
        horizontal=True,
        label_visibility="collapsed",
        key=key,
    )


def _render_period_selector():
    try:
        box = st.container(border=True)
    except TypeError:
        box = st.container()

    with box:
        if st.session_state.get("mobile_layout", False):
            st.caption("圖表模式")
            mode = _select_control(
                label="圖表模式",
                options=["分時走勢", "K線走勢", "多週期分析"],
                default="分時走勢",
                key="chart_mode_selector",
            )

            st.caption("週期")
            period = _select_control(
                label="週期",
                options=["1分", "5分", "15分", "30分", "日"],
                default="1分",
                key="chart_period_selector",
            )

            st.caption("工具")
            tool1, tool2, tool3 = st.columns(3, gap="small")

            with tool1:
                st.button("技術", key="chart_tool_indicator", use_container_width=True)

            with tool2:
                st.button("畫線", key="chart_tool_line", use_container_width=True)

            with tool3:
                is_full = st.session_state.get("chart_fullscreen", False)
                clicked = st.button(
                    "返回" if is_full else "全屏",
                    key="chart_tool_full",
                    use_container_width=True,
                )
                if clicked:
                    st.session_state.chart_fullscreen = not is_full
                    st.rerun()

            return mode, period

        col1, col2, col3 = st.columns(
            [1.1, 1.1, 0.9],
            gap="small",
            vertical_alignment="top",
        )

        with col1:
            st.caption("圖表模式")
            mode = _select_control(
                label="圖表模式",
                options=["分時走勢", "K線走勢", "多週期分析"],
                default="分時走勢",
                key="chart_mode_selector",
            )

        with col2:
            st.caption("週期")
            period = _select_control(
                label="週期",
                options=["1分", "5分", "15分", "30分", "日"],
                default="1分",
                key="chart_period_selector",
            )

        with col3:
            st.caption("工具")
            tool1, tool2, tool3 = st.columns(3, gap="small")

            with tool1:
                st.button(
                    "技術",
                    key="chart_tool_indicator",
                    use_container_width=True,
                )

            with tool2:
                st.button(
                    "畫線",
                    key="chart_tool_line",
                    use_container_width=True,
                )

            with tool3:
                is_full = st.session_state.get("chart_fullscreen", False)

                clicked = st.button(
                    "返回" if is_full else "全屏",
                    key="chart_tool_full",
                    use_container_width=True,
                )

                if clicked:
                    st.session_state.chart_fullscreen = not is_full
                    st.rerun()

    return mode, period


def _render_chart_toolbar(
    mode,
    period,
    current_price,
    vwap,
    ema5,
    ema20,
    ema60,
    data_points,
):
    current_price = _safe_float(current_price)
    vwap = _safe_float(vwap)
    ema5 = _safe_float(ema5)
    ema20 = _safe_float(ema20)
    ema60 = _safe_float(ema60)

    if current_price >= vwap:
        price_state = "站上 VWAP"
        price_color = UP_COLOR
    else:
        price_state = "跌破 VWAP"
        price_color = DOWN_COLOR

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            margin: 0;
            padding: 0;
            background: transparent;
            font-family: Arial, "Microsoft JhengHei", sans-serif;
            color: {TEXT};
            overflow: hidden;
        }}

        .wrap {{
            background: {CARD_BG};
            border: 1px solid {CARD_BORDER};
            border-radius: 13px;
            padding: 7px 10px;
            box-sizing: border-box;
            width: 100%;
        }}

        .line {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
            width: 100%;
        }}

        .left {{
            display: flex;
            align-items: center;
            gap: 7px;
            white-space: nowrap;
        }}

        .mode {{
            color: #ffffff;
            font-size: 12px;
            font-weight: 900;
        }}

        .pill {{
            color: #ffffff;
            background: rgba(59,130,246,0.22);
            border: 1px solid rgba(59,130,246,0.55);
            border-radius: 999px;
            padding: 3px 8px;
            font-size: 11px;
            font-weight: 900;
        }}

        .right {{
            display: flex;
            align-items: center;
            gap: 9px;
            color: {SUBTEXT};
            font-size: 11.5px;
            white-space: nowrap;
            overflow: hidden;
        }}

        .right b {{
            color: {TEXT};
        }}

        .state {{
            color: {price_color};
            font-weight: 900;
        }}

        @media (max-width: 900px) {{
            .line {{
                align-items: flex-start;
                flex-direction: column;
            }}

            .right {{
                flex-wrap: wrap;
                white-space: normal;
            }}
        }}
    </style>
</head>

<body>
    <div class="wrap">
        <div class="line">

            <div class="left">
                <span class="mode">{mode}</span>
                <span class="pill">{period}</span>
                <span class="pill">資料 {data_points}</span>
            </div>

            <div class="right">
                <span>Price <b>{current_price:.2f}</b></span>
                <span>VWAP <b>{vwap:.2f}</b></span>
                <span>EMA5 <b>{ema5:.2f}</b></span>
                <span>EMA20 <b>{ema20:.2f}</b></span>
                <span>EMA60 <b>{ema60:.2f}</b></span>
                <span class="state">{price_state}</span>
            </div>

        </div>
    </div>
</body>
</html>
"""

    render_html(html, height=66)


def _trend_state(price, vwap, ema5, ema20, macd, signal):
    bull = 0
    bear = 0

    if price > vwap:
        bull += 1
    elif price < vwap:
        bear += 1

    if ema5 > ema20:
        bull += 1
    elif ema5 < ema20:
        bear += 1

    if macd > signal:
        bull += 1
    elif macd < signal:
        bear += 1

    if price > ema5:
        bull += 1
    elif price < ema5:
        bear += 1

    if bull >= 3:
        return "BULL"

    if bear >= 3:
        return "BEAR"

    return "WAIT"


def _build_signal_points(
    x,
    prices,
    vwaps,
    ema5,
    ema20,
    macd_line,
    signal_line,
    decision=None,
):
    buy_x = []
    buy_y = []
    buy_text = []

    sell_x = []
    sell_y = []
    sell_text = []

    n = len(prices)

    if n < 10:
        return {
            "buy_x": [],
            "buy_y": [],
            "buy_text": [],
            "sell_x": [],
            "sell_y": [],
            "sell_text": [],
        }

    min_gap = max(18, n // 12)
    last_mark_index = -999
    current_position = "NONE"

    for i in range(2, n):
        price = _safe_float(prices[i])
        vwap = _safe_float(vwaps[i]) if i < len(vwaps) else price
        e5 = _safe_float(ema5[i]) if i < len(ema5) else price
        e20 = _safe_float(ema20[i]) if i < len(ema20) else price
        macd = _safe_float(macd_line[i]) if i < len(macd_line) else 0
        sig = _safe_float(signal_line[i]) if i < len(signal_line) else 0

        prev_price = _safe_float(prices[i - 1])
        prev_vwap = _safe_float(vwaps[i - 1]) if i - 1 < len(vwaps) else prev_price
        prev_e5 = _safe_float(ema5[i - 1]) if i - 1 < len(ema5) else prev_price
        prev_e20 = _safe_float(ema20[i - 1]) if i - 1 < len(ema20) else prev_price
        prev_macd = _safe_float(macd_line[i - 1]) if i - 1 < len(macd_line) else 0
        prev_sig = _safe_float(signal_line[i - 1]) if i - 1 < len(signal_line) else 0

        state = _trend_state(price, vwap, e5, e20, macd, sig)
        prev_state = _trend_state(
            prev_price,
            prev_vwap,
            prev_e5,
            prev_e20,
            prev_macd,
            prev_sig,
        )

        enough_gap = i - last_mark_index >= min_gap

        if state == "BULL" and prev_state != "BULL" and current_position != "LONG" and enough_gap:
            buy_x.append(x[i])
            buy_y.append(price)
            buy_text.append("買進訊號")
            current_position = "LONG"
            last_mark_index = i

        elif state == "BEAR" and prev_state != "BEAR" and current_position == "LONG" and enough_gap:
            sell_x.append(x[i])
            sell_y.append(price)
            sell_text.append("賣出訊號")
            current_position = "NONE"
            last_mark_index = i

    decision = decision or {}
    action = decision.get("action", "WAIT")
    score = _safe_int(decision.get("score", 0))

    if n >= 1 and score >= 75:
        if action == "BUY":
            if not buy_x or buy_x[-1] != x[-1]:
                buy_x.append(x[-1])
                buy_y.append(prices[-1])
                buy_text.append("即時買進觀察")

        elif action == "SELL":
            if not sell_x or sell_x[-1] != x[-1]:
                sell_x.append(x[-1])
                sell_y.append(prices[-1])
                sell_text.append("即時賣出觀察")

    max_marks = 4

    return {
        "buy_x": buy_x[-max_marks:],
        "buy_y": buy_y[-max_marks:],
        "buy_text": buy_text[-max_marks:],
        "sell_x": sell_x[-max_marks:],
        "sell_y": sell_y[-max_marks:],
        "sell_text": sell_text[-max_marks:],
    }


def _add_signal_markers(
    fig,
    x,
    prices,
    vwaps,
    ema5,
    ema20,
    macd_line,
    signal_line,
    decision=None,
):
    signals = _build_signal_points(
        x=x,
        prices=prices,
        vwaps=vwaps,
        ema5=ema5,
        ema20=ema20,
        macd_line=macd_line,
        signal_line=signal_line,
        decision=decision,
    )

    price_high = max(prices) if prices else 0
    price_low = min(prices) if prices else 0
    price_range = max(price_high - price_low, 0.01)

    arrow_gap = price_range * 0.055

    if signals["buy_x"]:
        fig.add_trace(
            go.Scatter(
                x=signals["buy_x"],
                y=signals["buy_y"],
                mode="markers",
                name="買進訊號",
                marker=dict(
                    symbol="triangle-up",
                    size=14,
                    color=UP_COLOR,
                    line=dict(
                        color="#ffffff",
                        width=0.5,
                    ),
                ),
                hovertemplate="買進訊號<br>%{x}<br>%{y:.2f}<extra></extra>",
            ),
            row=1,
            col=1,
        )

        for bx, by, text in zip(
            signals["buy_x"],
            signals["buy_y"],
            signals["buy_text"],
        ):
            fig.add_annotation(
                x=bx,
                y=by - arrow_gap,
                text=text,
                showarrow=True,
                arrowhead=2,
                ax=0,
                ay=22,
                bgcolor="rgba(0,230,118,0.16)",
                bordercolor=UP_COLOR,
                borderwidth=1,
                borderpad=4,
                font=dict(
                    color=UP_COLOR,
                    size=11,
                ),
                row=1,
                col=1,
            )

    if signals["sell_x"]:
        fig.add_trace(
            go.Scatter(
                x=signals["sell_x"],
                y=signals["sell_y"],
                mode="markers",
                name="賣出訊號",
                marker=dict(
                    symbol="triangle-down",
                    size=14,
                    color=DOWN_COLOR,
                    line=dict(
                        color="#ffffff",
                        width=0.5,
                    ),
                ),
                hovertemplate="賣出訊號<br>%{x}<br>%{y:.2f}<extra></extra>",
            ),
            row=1,
            col=1,
        )

        for sx, sy, text in zip(
            signals["sell_x"],
            signals["sell_y"],
            signals["sell_text"],
        ):
            fig.add_annotation(
                x=sx,
                y=sy + arrow_gap,
                text=text,
                showarrow=True,
                arrowhead=2,
                ax=0,
                ay=-22,
                bgcolor="rgba(255,82,82,0.16)",
                bordercolor=DOWN_COLOR,
                borderwidth=1,
                borderpad=4,
                font=dict(
                    color=DOWN_COLOR,
                    size=11,
                ),
                row=1,
                col=1,
            )


def _add_right_price_label(fig, current_price, color):
    fig.add_hline(
        y=current_price,
        line=dict(
            color="#00e5ff",
            width=1.1,
            dash="dot",
        ),
        row=1,
        col=1,
    )

    fig.add_annotation(
        x=1.01,
        y=current_price,
        xref="paper",
        yref="y",
        text=f"{current_price:.2f}",
        showarrow=False,
        bgcolor=color,
        bordercolor=color,
        borderwidth=1,
        borderpad=4,
        xanchor="left",
        yanchor="middle",
        font=dict(
            color="#ffffff",
            size=10,
        ),
    )


def _apply_intraday_xaxis(fig, x_values):
    dt_values = [
        x
        for x in x_values
        if isinstance(x, datetime)
    ]

    if not dt_values:
        return

    base = dt_values[0].replace(
        hour=9,
        minute=0,
        second=0,
        microsecond=0,
    )

    end = dt_values[0].replace(
        hour=13,
        minute=30,
        second=0,
        microsecond=0,
    )

    for row in [1, 2, 3]:
        fig.update_xaxes(
            range=[base, end],
            tickformat="%H:%M",
            dtick=30 * 60 * 1000,
            row=row,
            col=1,
        )


def _add_common_layout(fig, chart_key, x_values=None):
    is_full = st.session_state.get("chart_fullscreen", False)

    mobile_layout = st.session_state.get("mobile_layout", False)
    chart_height = 740 if is_full else (210 if mobile_layout else 220)
    right_margin = 42 if mobile_layout else 70

    fig.update_layout(
        height=chart_height,
        margin=dict(
            l=8 if mobile_layout else 12,
            r=right_margin,
            t=18,
            b=8,
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#0b0f16",
        font=dict(
            color=TEXT,
            size=10,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(
                size=10,
                color=TEXT,
            ),
        ),
        hovermode="x unified",
        bargap=0.10,
        xaxis_rangeslider_visible=False,
    )

    for row in [1, 2, 3]:
        fig.update_xaxes(
            showgrid=True,
            gridcolor="rgba(255,255,255,0.045)",
            zeroline=False,
            showline=False,
            tickfont=dict(
                color=SUBTEXT,
                size=9,
            ),
            row=row,
            col=1,
        )

        fig.update_yaxes(
            side="right",
            gridcolor="rgba(255,255,255,0.075)",
            zeroline=False,
            showline=False,
            tickfont=dict(
                color=TEXT,
                size=9,
            ),
            row=row,
            col=1,
        )

    if x_values is not None:
        _apply_intraday_xaxis(fig, x_values)

    st.plotly_chart(
        fig,
        use_container_width=True,
        key=chart_key,
        config={
            "displayModeBar": True,
            "scrollZoom": True,
            "responsive": True,
        },
    )


def _render_line_chart(
    clean_prices,
    clean_volumes,
    clean_vwap,
    x,
    mode,
    period,
    decision=None,
):
    n = len(clean_prices)

    current_price = clean_prices[-1]
    prev_price = clean_prices[-2] if len(clean_prices) >= 2 else current_price

    price_color = UP_COLOR if current_price >= prev_price else DOWN_COLOR

    ema5 = _ema(clean_prices, 5)
    ema20 = _ema(clean_prices, 20)
    ema60 = _ema(clean_prices, 60)

    current_vwap = current_price

    valid_vwap = [
        v
        for v in clean_vwap
        if v is not None and _safe_float(v) > 0
    ]

    if valid_vwap:
        current_vwap = valid_vwap[-1]

    _render_chart_toolbar(
        mode=mode,
        period=period,
        current_price=current_price,
        vwap=current_vwap,
        ema5=ema5[-1] if ema5 else current_price,
        ema20=ema20[-1] if ema20 else current_price,
        ema60=ema60[-1] if ema60 else current_price,
        data_points=n,
    )

    macd_line, signal_line, hist = _macd(clean_prices)

    volume_colors = []

    for i, p in enumerate(clean_prices):
        if i == 0:
            volume_colors.append(price_color)
        else:
            if p >= clean_prices[i - 1]:
                volume_colors.append(UP_COLOR)
            else:
                volume_colors.append(DOWN_COLOR)

    hist_colors = []

    for h in hist:
        if h >= 0:
            hist_colors.append(UP_COLOR)
        else:
            hist_colors.append(DOWN_COLOR)

    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.60, 0.22, 0.18],
        vertical_spacing=0.025,
    )

    fig.add_trace(
        go.Scatter(
            x=x,
            y=clean_prices,
            mode="lines",
            name="Price",
            line=dict(
                color=price_color,
                width=2.2,
            ),
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=x,
            y=ema5,
            mode="lines",
            name="EMA5",
            line=dict(color="#facc15", width=1.3),
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=x,
            y=ema20,
            mode="lines",
            name="EMA20",
            line=dict(color="#fb7185", width=1.3),
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=x,
            y=ema60,
            mode="lines",
            name="EMA60",
            line=dict(color="#a855f7", width=1.3),
        ),
        row=1,
        col=1,
    )

    if clean_vwap and any(v is not None and v > 0 for v in clean_vwap):
        fig.add_trace(
            go.Scatter(
                x=x,
                y=clean_vwap,
                mode="lines",
                name="VWAP",
                connectgaps=True,
                line=dict(
                    color="#22c55e",
                    width=1.7,
                    dash="dot",
                ),
            ),
            row=1,
            col=1,
        )

    _add_signal_markers(
        fig=fig,
        x=x,
        prices=clean_prices,
        vwaps=clean_vwap,
        ema5=ema5,
        ema20=ema20,
        macd_line=macd_line,
        signal_line=signal_line,
        decision=decision,
    )

    fig.add_trace(
        go.Bar(
            x=x,
            y=clean_volumes,
            name="Volume",
            marker=dict(
                color=volume_colors,
                opacity=0.75,
            ),
        ),
        row=2,
        col=1,
    )

    fig.add_trace(
        go.Bar(
            x=x,
            y=hist,
            name="MACD Hist",
            marker=dict(
                color=hist_colors,
                opacity=0.75,
            ),
        ),
        row=3,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=x,
            y=macd_line,
            mode="lines",
            name="MACD",
            line=dict(color="#38bdf8", width=1.4),
        ),
        row=3,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=x,
            y=signal_line,
            mode="lines",
            name="Signal",
            line=dict(color="#f97316", width=1.2),
        ),
        row=3,
        col=1,
    )

    fig.add_hline(
        y=0,
        line=dict(
            color="rgba(255,255,255,0.18)",
            width=1,
        ),
        row=3,
        col=1,
    )

    price_candidates = clean_prices[:]

    for v in clean_vwap:
        if v is not None and v > 0:
            price_candidates.append(v)

    high = max(price_candidates)
    low = min(price_candidates)

    price_padding = max(
        (high - low) * 0.35,
        current_price * 0.001,
    )

    fig.update_yaxes(
        range=[
            low - price_padding,
            high + price_padding,
        ],
        row=1,
        col=1,
    )

    max_volume = max(clean_volumes) if clean_volumes else 1

    fig.update_yaxes(
        range=[
            0,
            max(max_volume * 1.30, 1),
        ],
        row=2,
        col=1,
    )

    _add_right_price_label(
        fig=fig,
        current_price=current_price,
        color=price_color,
    )

    _add_common_layout(
        fig,
        chart_key=f"line_chart_{mode}_{period}",
        x_values=x,
    )


def _render_k_chart(ohlc, mode, period, decision=None):
    x = ohlc["x"]
    opens = ohlc["open"]
    highs = ohlc["high"]
    lows = ohlc["low"]
    closes = ohlc["close"]
    volumes = [_to_lot(v) for v in ohlc["volume"]]
    vwaps = ohlc["vwap"]

    if not closes:
        st.caption("尚無 K 線資料")
        return

    n = len(closes)

    current_price = closes[-1]
    current_vwap = vwaps[-1] if vwaps else current_price

    ema5 = _ema(closes, 5)
    ema20 = _ema(closes, 20)
    ema60 = _ema(closes, 60)

    _render_chart_toolbar(
        mode=mode,
        period=period,
        current_price=current_price,
        vwap=current_vwap,
        ema5=ema5[-1] if ema5 else current_price,
        ema20=ema20[-1] if ema20 else current_price,
        ema60=ema60[-1] if ema60 else current_price,
        data_points=n,
    )

    macd_line, signal_line, hist = _macd(closes)

    candle_colors = []

    for i in range(n):
        if closes[i] >= opens[i]:
            candle_colors.append(UP_COLOR)
        else:
            candle_colors.append(DOWN_COLOR)

    hist_colors = []

    for h in hist:
        if h >= 0:
            hist_colors.append(UP_COLOR)
        else:
            hist_colors.append(DOWN_COLOR)

    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.60, 0.22, 0.18],
        vertical_spacing=0.025,
    )

    fig.add_trace(
        go.Candlestick(
            x=x,
            open=opens,
            high=highs,
            low=lows,
            close=closes,
            name="K",
            increasing=dict(
                line=dict(color=UP_COLOR, width=1.1),
                fillcolor=UP_COLOR,
            ),
            decreasing=dict(
                line=dict(color=DOWN_COLOR, width=1.1),
                fillcolor=DOWN_COLOR,
            ),
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=x,
            y=ema5,
            mode="lines",
            name="EMA5",
            line=dict(color="#facc15", width=1.2),
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=x,
            y=ema20,
            mode="lines",
            name="EMA20",
            line=dict(color="#fb7185", width=1.2),
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=x,
            y=ema60,
            mode="lines",
            name="EMA60",
            line=dict(color="#a855f7", width=1.2),
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=x,
            y=vwaps,
            mode="lines",
            name="VWAP",
            line=dict(
                color="#22c55e",
                width=1.7,
                dash="dot",
            ),
        ),
        row=1,
        col=1,
    )

    _add_signal_markers(
        fig=fig,
        x=x,
        prices=closes,
        vwaps=vwaps,
        ema5=ema5,
        ema20=ema20,
        macd_line=macd_line,
        signal_line=signal_line,
        decision=decision,
    )

    fig.add_trace(
        go.Bar(
            x=x,
            y=volumes,
            name="Volume",
            marker=dict(
                color=candle_colors,
                opacity=0.75,
            ),
        ),
        row=2,
        col=1,
    )

    fig.add_trace(
        go.Bar(
            x=x,
            y=hist,
            name="MACD Hist",
            marker=dict(
                color=hist_colors,
                opacity=0.75,
            ),
        ),
        row=3,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=x,
            y=macd_line,
            mode="lines",
            name="MACD",
            line=dict(color="#38bdf8", width=1.4),
        ),
        row=3,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=x,
            y=signal_line,
            mode="lines",
            name="Signal",
            line=dict(color="#f97316", width=1.2),
        ),
        row=3,
        col=1,
    )

    fig.add_hline(
        y=0,
        line=dict(
            color="rgba(255,255,255,0.18)",
            width=1,
        ),
        row=3,
        col=1,
    )

    price_candidates = highs + lows + vwaps

    high = max(price_candidates)
    low = min(price_candidates)

    price_padding = max(
        (high - low) * 0.35,
        current_price * 0.001,
    )

    fig.update_yaxes(
        range=[
            low - price_padding,
            high + price_padding,
        ],
        row=1,
        col=1,
    )

    max_volume = max(volumes) if volumes else 1

    fig.update_yaxes(
        range=[
            0,
            max(max_volume * 1.30, 1),
        ],
        row=2,
        col=1,
    )

    _add_right_price_label(
        fig=fig,
        current_price=current_price,
        color=UP_COLOR if closes[-1] >= opens[-1] else DOWN_COLOR,
    )

    _add_common_layout(
        fig,
        chart_key=f"k_chart_{mode}_{period}",
        x_values=x,
    )


def render_chart(
    prices,
    volumes,
    vwap_values=None,
    time_values=None,
    decision=None,
    trade_alert=None,
):
    st.markdown("### 📈 分時 / K線 / VWAP / MACD")

    if not prices:
        st.caption("等待行情資料中...")
        return

    mode, period = _render_period_selector()

    if mode == "K線走勢":
        ohlc = _aggregate_ohlc(
            prices=prices,
            volumes=volumes,
            vwaps=vwap_values or [],
            times=time_values or [],
            period=period,
        )

        _render_k_chart(
            ohlc=ohlc,
            mode=mode,
            period=period,
            decision=decision,
        )

        return

    if mode == "多週期分析":
        render_multi_period_analysis(
            prices=prices,
            volumes=volumes,
            vwap_values=vwap_values or [],
            time_values=time_values or [],
        )
        return

    clean_prices, clean_volumes, clean_vwap, x = _aggregate_line(
        prices=prices,
        volumes=volumes,
        vwaps=vwap_values or [],
        times=time_values or [],
        period=period,
    )

    if not clean_prices:
        st.caption("尚無有效價格資料")
        return

    clean_prices = clean_prices[-270:]
    clean_volumes = clean_volumes[-270:]
    clean_vwap = clean_vwap[-270:]
    x = x[-270:]

    clean_volumes = [
        _to_lot(v)
        for v in clean_volumes
    ]

    _render_line_chart(
        clean_prices=clean_prices,
        clean_volumes=clean_volumes,
        clean_vwap=clean_vwap,
        x=x,
        mode=mode,
        period=period,
        decision=decision,
    )
