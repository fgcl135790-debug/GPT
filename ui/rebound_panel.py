import streamlit as st
import streamlit.components.v1 as components
from html import escape

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


def _safe_int(value, default=0):
    try:
        return int(round(float(value)))
    except Exception:
        return default


def render_rebound_panel(decision, trade_alert):

    rebound = _safe_int(decision.get("rebound", 0))
    fake_signal = decision.get("fake_signal", "NONE")
    fake_text = escape(str(decision.get("fake_text", "未出現明顯突破或跌破")))

    alert_title = escape(str(trade_alert.get("title", "等待訊號")))
    alert_message = escape(str(trade_alert.get("message", "-")))

    if rebound >= 60:
        color = UP_COLOR
        status = "反彈條件偏強"
        desc = "短線有反彈機會，但仍需配合量能與 VWAP。"

    elif rebound <= 35:
        color = DOWN_COLOR
        status = "反彈條件偏弱"
        desc = "反彈力道不足，追多風險較高。"

    else:
        color = WAIT_COLOR
        status = "反彈條件中性"
        desc = "多空仍在拉鋸，等待方向確認。"

    if fake_signal == "FAKE_BREAKOUT":
        fake_status = "疑似假突破"
        fake_color = WAIT_COLOR

    elif fake_signal == "FAKE_BREAKDOWN":
        fake_status = "疑似假跌破"
        fake_color = WAIT_COLOR

    elif fake_signal == "REAL_BREAKOUT":
        fake_status = "有效突破"
        fake_color = UP_COLOR

    elif fake_signal == "REAL_BREAKDOWN":
        fake_status = "有效跌破"
        fake_color = DOWN_COLOR

    else:
        fake_status = "無明顯假突破"
        fake_color = SUBTEXT

    degree = int(rebound * 3.6)

    st.markdown("### 🔁 反彈機率分析")

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
            padding: 12px;
            box-sizing: border-box;
            width: 100%;
        }}

        .top {{
            display: grid;
            grid-template-columns: 86px 1fr;
            gap: 12px;
            align-items: center;
        }}

        .ring {{
            width: 78px;
            height: 78px;
            border-radius: 50%;
            background:
                conic-gradient({color} 0deg, {color} {degree}deg, rgba(255,255,255,0.10) {degree}deg, rgba(255,255,255,0.10) 360deg);
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .inner {{
            width: 57px;
            height: 57px;
            border-radius: 50%;
            background: #0b111c;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            border: 1px solid rgba(255,255,255,0.06);
        }}

        .num {{
            font-size: 22px;
            font-weight: 900;
            color: #ffffff;
            line-height: 1;
        }}

        .unit {{
            font-size: 10px;
            color: {SUBTEXT};
            margin-top: 2px;
        }}

        .status {{
            color: {color};
            font-size: 18px;
            font-weight: 900;
            margin-bottom: 5px;
        }}

        .desc {{
            color: {SUBTEXT};
            font-size: 12px;
            line-height: 1.4;
        }}

        .fake {{
            margin-top: 10px;
            padding-top: 9px;
            border-top: 1px solid rgba(255,255,255,0.08);
        }}

        .fake-title {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 5px;
        }}

        .fake-left {{
            color: {SUBTEXT};
            font-size: 12px;
            font-weight: 700;
        }}

        .fake-right {{
            color: {fake_color};
            font-size: 13px;
            font-weight: 900;
        }}

        .fake-text {{
            color: {SUBTEXT};
            font-size: 11.5px;
            line-height: 1.35;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}

        .alert {{
            margin-top: 9px;
            background: rgba(255,255,255,0.035);
            border-radius: 10px;
            padding: 8px;
            border-left: 4px solid {color};
        }}

        .alert-title {{
            color: {color};
            font-size: 12.5px;
            font-weight: 900;
            margin-bottom: 3px;
        }}

        .alert-msg {{
            color: {SUBTEXT};
            font-size: 11.5px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
    </style>
</head>

<body>
    <div class="card">

        <div class="top">
            <div class="ring">
                <div class="inner">
                    <div class="num">{rebound}</div>
                    <div class="unit">%</div>
                </div>
            </div>

            <div>
                <div class="status">{status}</div>
                <div class="desc">{desc}</div>
            </div>
        </div>

        <div class="fake">
            <div class="fake-title">
                <div class="fake-left">假突破 / 假跌破</div>
                <div class="fake-right">{fake_status}</div>
            </div>

            <div class="fake-text">
                {fake_text}
            </div>
        </div>

        <div class="alert">
            <div class="alert-title">進出場狀態｜{alert_title}</div>
            <div class="alert-msg">{alert_message}</div>
        </div>

    </div>
</body>
</html>
"""

    render_html(html, height=460)
