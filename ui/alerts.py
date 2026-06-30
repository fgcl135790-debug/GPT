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


def _level_style(level):
    level = str(level or "info").lower()

    if level == "success":
        return {
            "color": UP_COLOR,
            "label": "偏多",
            "bg": "rgba(255,82,82,0.10)",
        }

    if level == "danger":
        return {
            "color": DOWN_COLOR,
            "label": "偏空",
            "bg": "rgba(0,230,118,0.10)",
        }

    if level == "warning":
        return {
            "color": WAIT_COLOR,
            "label": "風險",
            "bg": "rgba(255,193,7,0.10)",
        }

    return {
        "color": "#60a5fa",
        "label": "監控",
        "bg": "rgba(96,165,250,0.10)",
    }


def render_alerts(alerts):

    alerts = alerts or []

    # 只顯示最重要 3 條，避免右側被警示撐爆
    display_alerts = alerts[:3]

    if not display_alerts:
        display_alerts = [
            {
                "title": "監控中",
                "message": "目前沒有重大警示，等待更明確的多空訊號。",
                "level": "info",
                "icon": "👀",
            }
        ]

    rows_html = ""

    for alert in display_alerts:

        title = escape(str(alert.get("title", "監控中")))
        message = escape(str(alert.get("message", "-")))
        icon = escape(str(alert.get("icon", "ℹ️")))
        level = alert.get("level") or alert.get("severity") or "info"

        style = _level_style(level)

        rows_html += f"""
        <div class="alert-row" style="border-left-color:{style["color"]}; background:{style["bg"]};">
            <div class="alert-top">
                <div class="alert-title" style="color:{style["color"]};">
                    <span class="icon">{icon}</span>
                    {title}
                </div>

                <div class="badge" style="color:{style["color"]}; border-color:{style["color"]};">
                    {style["label"]}
                </div>
            </div>

            <div class="alert-msg">
                {message}
            </div>
        </div>
        """

    more_count = max(len(alerts) - len(display_alerts), 0)

    more_html = ""

    if more_count > 0:
        more_html = f"""
        <div class="more">
            另有 {more_count} 則警示已收合
        </div>
        """

    st.markdown("### 🔔 即時警示")

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
            padding: 10px;
            box-sizing: border-box;
            width: 100%;
        }}

        .alert-row {{
            border-left: 4px solid;
            border-radius: 10px;
            padding: 8px 9px;
            margin-bottom: 7px;
            box-sizing: border-box;
        }}

        .alert-row:last-child {{
            margin-bottom: 0;
        }}

        .alert-top {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 8px;
            margin-bottom: 4px;
        }}

        .alert-title {{
            font-size: 12.5px;
            font-weight: 900;
            line-height: 1.25;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}

        .icon {{
            margin-right: 4px;
        }}

        .badge {{
            font-size: 10px;
            font-weight: 900;
            border: 1px solid;
            border-radius: 999px;
            padding: 2px 7px;
            white-space: nowrap;
        }}

        .alert-msg {{
            color: {SUBTEXT};
            font-size: 11.2px;
            line-height: 1.35;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}

        .more {{
            margin-top: 7px;
            padding-top: 7px;
            border-top: 1px solid rgba(255,255,255,0.08);
            color: {SUBTEXT};
            font-size: 11px;
            text-align: right;
        }}
    </style>
</head>

<body>
    <div class="card">
        {rows_html}
        {more_html}
    </div>
</body>
</html>
"""

    render_html(html, height=300)
