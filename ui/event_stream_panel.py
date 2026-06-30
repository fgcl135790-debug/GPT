import streamlit as st
import streamlit.components.v1 as components
from html import escape
from datetime import datetime

from ui.theme import (
    UP_COLOR,
    DOWN_COLOR,
    WAIT_COLOR,
    CARD_BG,
    CARD_BORDER,
    TEXT,
    SUBTEXT,
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


def _fmt_time(value):
    if value is None:
        return "-"

    if isinstance(value, datetime):
        return value.strftime("%H:%M:%S")

    text = str(value)

    try:
        dt = datetime.fromisoformat(text)
        return dt.strftime("%H:%M:%S")
    except Exception:
        return text[-8:] if len(text) >= 8 else text


def _direction_style(direction):
    direction = str(direction or "UNKNOWN").upper()

    if direction == "BUY":
        return {
            "color": UP_COLOR,
            "label": "買方大單",
            "icon": "🔴",
        }

    if direction == "SELL":
        return {
            "color": DOWN_COLOR,
            "label": "賣方大單",
            "icon": "🟢",
        }

    return {
        "color": WAIT_COLOR,
        "label": "方向不明",
        "icon": "🟡",
    }


def _normalize_event(item):
    item = item or {}

    direction = str(item.get("direction", "UNKNOWN")).upper()
    style = _direction_style(direction)

    price = item.get("price", "-")
    volume_lot = item.get("volume_lot", item.get("volume", "-"))
    strength = item.get("strength", "-")
    time_text = _fmt_time(item.get("time", item.get("created_at", None)))

    direction_text = item.get("direction_text", style["label"])

    try:
        price_text = f"{float(price):.2f}"
    except Exception:
        price_text = str(price)

    try:
        volume_text = f"{float(volume_lot):.0f}"
    except Exception:
        volume_text = str(volume_lot)

    return {
        "direction": direction,
        "color": style["color"],
        "icon": style["icon"],
        "label": style["label"],
        "time": time_text,
        "price": price_text,
        "volume_lot": volume_text,
        "strength": str(strength),
        "direction_text": str(direction_text),
    }


def _event_row_html(event):
    color = event["color"]

    return f"""
    <div class="event-row">
        <div class="event-time">{escape(event["time"])}</div>

        <div class="event-main">
            <div class="event-title" style="color:{color};">
                <span>{escape(event["icon"])}</span>
                <span>{escape(event["label"])}</span>
            </div>

            <div class="event-desc">
                {escape(event["direction_text"])}
            </div>
        </div>

        <div class="event-price">
            {escape(event["price"])}
        </div>

        <div class="event-volume" style="color:{color};">
            {escape(event["volume_lot"])} 張
        </div>

        <div class="event-strength">
            {escape(event["strength"])}
        </div>
    </div>
    """


def render_event_stream_panel(big_order_log, decision=None):
    big_order_log = big_order_log or []
    decision = decision or {}

    latest_items = big_order_log[-8:]
    latest_items = list(reversed(latest_items))

    events = [
        _normalize_event(item)
        for item in latest_items
    ]

    buy_count = 0
    sell_count = 0
    buy_volume = 0
    sell_volume = 0

    for item in big_order_log[-30:]:
        direction = str(item.get("direction", "UNKNOWN")).upper()
        volume = _safe_float(item.get("volume_lot", item.get("volume", 0)))

        if direction == "BUY":
            buy_count += 1
            buy_volume += volume

        elif direction == "SELL":
            sell_count += 1
            sell_volume += volume

    action = decision.get("action", "WAIT")
    score = _safe_int(decision.get("score", 0))
    multi_status = decision.get("multi_period_status", "盤整觀望")

    if buy_volume > sell_volume * 1.25 and buy_volume > 0:
        summary = "買方大單主導"
        summary_color = UP_COLOR
        summary_desc = "近期主力大單偏向買方，觀察是否持續承接。"

    elif sell_volume > buy_volume * 1.25 and sell_volume > 0:
        summary = "賣方大單主導"
        summary_color = DOWN_COLOR
        summary_desc = "近期主力大單偏向賣方，反彈時留意壓力。"

    elif buy_volume > 0 or sell_volume > 0:
        summary = "大單多空拉鋸"
        summary_color = WAIT_COLOR
        summary_desc = "買賣大單互有出現，短線可能震盪。"

    else:
        summary = "等待主力大單"
        summary_color = WAIT_COLOR
        summary_desc = "尚未偵測到明顯主力大單。"

    if events:
        rows_html = ""

        for event in events:
            rows_html += _event_row_html(event)

    else:
        rows_html = f"""
        <div class="empty">
            尚未偵測到大單事件，系統持續監控中。
        </div>
        """

    st.markdown("### 🐋 大單紀錄 / 主力事件流")

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

        .card {{
            background: {CARD_BG};
            border: 1px solid {CARD_BORDER};
            border-radius: 14px;
            padding: 11px;
            box-sizing: border-box;
            width: 100%;
        }}

        .summary {{
            display: grid;
            grid-template-columns: 1.1fr 0.9fr 0.9fr 0.9fr;
            gap: 8px;
            margin-bottom: 10px;
        }}

        .summary-main {{
            background: rgba(255,255,255,0.035);
            border-left: 4px solid {summary_color};
            border-radius: 10px;
            padding: 8px 10px;
            box-sizing: border-box;
        }}

        .summary-label {{
            color: {SUBTEXT};
            font-size: 11px;
            margin-bottom: 3px;
        }}

        .summary-value {{
            color: {summary_color};
            font-size: 19px;
            font-weight: 900;
            line-height: 1.1;
        }}

        .summary-desc {{
            color: {SUBTEXT};
            font-size: 11px;
            margin-top: 4px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}

        .box {{
            background: rgba(255,255,255,0.035);
            border-radius: 10px;
            padding: 8px 6px;
            text-align: center;
        }}

        .box-label {{
            color: {SUBTEXT};
            font-size: 10.5px;
            margin-bottom: 4px;
        }}

        .box-value {{
            color: {TEXT};
            font-size: 16px;
            font-weight: 900;
            line-height: 1.1;
        }}

        .table-head {{
            display: grid;
            grid-template-columns: 76px 1.2fr 78px 90px 74px;
            gap: 8px;
            padding: 7px 8px;
            color: {SUBTEXT};
            font-size: 11px;
            font-weight: 900;
            border-top: 1px solid rgba(255,255,255,0.08);
            border-bottom: 1px solid rgba(255,255,255,0.08);
        }}

        .event-row {{
            display: grid;
            grid-template-columns: 76px 1.2fr 78px 90px 74px;
            gap: 8px;
            align-items: center;
            padding: 8px;
            border-bottom: 1px solid rgba(255,255,255,0.055);
            box-sizing: border-box;
        }}

        .event-row:last-child {{
            border-bottom: none;
        }}

        .event-time {{
            color: {SUBTEXT};
            font-size: 11.5px;
            font-weight: 800;
        }}

        .event-title {{
            font-size: 12.5px;
            font-weight: 900;
            display: flex;
            gap: 5px;
            align-items: center;
        }}

        .event-desc {{
            color: {SUBTEXT};
            font-size: 10.8px;
            margin-top: 2px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}

        .event-price {{
            color: {TEXT};
            font-size: 12.5px;
            font-weight: 900;
            text-align: right;
        }}

        .event-volume {{
            font-size: 12.5px;
            font-weight: 900;
            text-align: right;
        }}

        .event-strength {{
            color: {TEXT};
            font-size: 11.5px;
            font-weight: 900;
            text-align: right;
        }}

        .empty {{
            color: {SUBTEXT};
            font-size: 12px;
            padding: 18px 8px;
            text-align: center;
            border-top: 1px solid rgba(255,255,255,0.08);
        }}

        @media (max-width: 900px) {{
            .summary {{
                grid-template-columns: 1fr 1fr;
            }}

            .table-head,
            .event-row {{
                grid-template-columns: 62px 1fr 70px 76px;
            }}

            .table-head div:nth-child(5),
            .event-strength {{
                display: none;
            }}
        }}
    </style>
</head>

<body>
    <div class="card">

        <div class="summary">
            <div class="summary-main">
                <div class="summary-label">主力事件結論</div>
                <div class="summary-value">{escape(summary)}</div>
                <div class="summary-desc">{escape(summary_desc)}</div>
            </div>

            <div class="box">
                <div class="box-label">買方大單</div>
                <div class="box-value" style="color:{UP_COLOR};">{buy_count}</div>
            </div>

            <div class="box">
                <div class="box-label">賣方大單</div>
                <div class="box-value" style="color:{DOWN_COLOR};">{sell_count}</div>
            </div>

            <div class="box">
                <div class="box-label">決策 / 分數</div>
                <div class="box-value" style="color:{summary_color};">{escape(str(action))} {score}</div>
            </div>
        </div>

        <div class="table-head">
            <div>時間</div>
            <div>事件</div>
            <div style="text-align:right;">價格</div>
            <div style="text-align:right;">張數</div>
            <div style="text-align:right;">強度</div>
        </div>

        {rows_html}

    </div>
</body>
</html>
"""

    render_html(html, height=520)
