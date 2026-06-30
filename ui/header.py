import streamlit as st
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


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def _risk_style(risk):
    text = str(risk)
    if "高" in text:
        return DOWN_COLOR, "高風險", "請降低追價"
    if "中" in text:
        return WAIT_COLOR, "中低風險", "風險可控"
    if "%" in text:
        value = _safe_int(text.replace("%", ""), 0)
        if value >= 60:
            return DOWN_COLOR, f"{value}%", "風險偏高"
        if value >= 30:
            return WAIT_COLOR, f"{value}%", "風險中等"
        return UP_COLOR, f"{value}%", "風險偏低"
    return WAIT_COLOR, text, "風險監控中"


def _force_style(bid_ratio):
    bid_ratio = _safe_float(bid_ratio, 1.0)
    if bid_ratio >= 1.5:
        return UP_COLOR, "主力吸籌", "籌碼集中偏多"
    if bid_ratio >= 1.15:
        return UP_COLOR, "買盤偏強", "買方略強"
    if bid_ratio <= 0.6:
        return DOWN_COLOR, "主力出貨", "賣壓明顯偏空"
    if bid_ratio <= 0.85:
        return DOWN_COLOR, "賣盤偏強", "賣方略強"
    return WAIT_COLOR, "主力觀望", "多空拉鋸"


def _status_style(signal, state):
    state_text = str(state)
    if signal == "BUY":
        return UP_COLOR, "多頭強勢", "趨勢向上"
    if signal == "SELL":
        return DOWN_COLOR, "空頭偏強", "趨勢向下"
    if "多" in state_text:
        return UP_COLOR, state_text, "趨勢偏多"
    if "空" in state_text:
        return DOWN_COLOR, state_text, "趨勢偏空"
    return WAIT_COLOR, state_text, "等待突破"


def render_header(
    name,
    stock_code,
    price,
    score,
    rebound,
    risk,
    state,
    signal,
    bid_ratio,
    now,
    connection_status="連線正常",
    data_source="真實盤",
):
    name = escape(str(name))
    stock_code = escape(str(stock_code))
    price = _safe_float(price)
    score = max(0, min(100, _safe_int(score)))
    rebound = max(0, min(100, _safe_int(rebound)))
    time_text = now.strftime("%H:%M:%S") if hasattr(now, "strftime") else str(now)
    conn_color = UP_COLOR if "正常" in str(connection_status) else DOWN_COLOR
    source_text = "即時更新" if data_source == "真實盤" else "模擬盤"
    rebound_color = UP_COLOR if rebound >= 60 else WAIT_COLOR if rebound >= 40 else DOWN_COLOR
    risk_color, risk_title, risk_sub = _risk_style(risk)
    force_color, force_title, force_sub = _force_style(bid_ratio)
    status_color, status_title, status_sub = _status_style(signal, state)

    html = f'''
<style>
    .topbar-mobile-safe {{
        width: 100%; display: flex; justify-content: space-between; align-items: center;
        gap: 10px; margin: 0 0 10px 0; padding: 2px 4px; box-sizing: border-box;
    }}
    .topbar-title {{
        display: flex; align-items: center; gap: 8px; font-size: 17px; font-weight: 900;
        color: {TEXT}; white-space: nowrap; min-width: 0;
    }}
    .topbar-info {{
        display: flex; align-items: center; justify-content: flex-end; gap: 14px;
        color: {SUBTEXT}; font-size: 12px; white-space: nowrap; min-width: 0;
    }}
    .topbar-dot {{
        display:inline-block; width:8px; height:8px; border-radius:99px;
        background:{conn_color}; box-shadow:0 0 8px {conn_color}; margin-right:5px;
    }}
    .status-grid-mobile-safe {{
        display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 10px;
        width: 100%; box-sizing: border-box; margin-bottom: 0.35rem;
    }}
    .status-card-mobile-safe {{
        background: {CARD_BG}; border: 1px solid {CARD_BORDER}; border-radius: 12px;
        padding: 11px 13px; min-height: 78px; box-sizing: border-box; min-width: 0;
    }}
    .status-label {{ color: {SUBTEXT}; font-size: 12px; margin-bottom: 6px; white-space: nowrap; }}
    .status-value {{ font-size: 25px; line-height: 1.05; font-weight: 900; margin-bottom: 6px; overflow-wrap: anywhere; }}
    .status-midvalue {{ font-size: 20px; line-height: 1.1; font-weight: 900; margin-bottom: 6px; overflow-wrap: anywhere; }}
    .status-sub {{ color: {SUBTEXT}; font-size: 11px; font-weight: 600; line-height: 1.25; }}
    .status-bar {{ width: 100%; height: 7px; background: rgba(255,255,255,0.12); border-radius: 999px; overflow: hidden; margin-top: 8px; }}
    .status-bar-fill {{ height: 100%; border-radius: 999px; }}

    @media (max-width: 760px) {{
        .topbar-mobile-safe {{ align-items: flex-start; flex-direction: column; gap: 4px; }}
        .topbar-title {{ width: 100%; font-size: 16px; overflow: hidden; text-overflow: ellipsis; }}
        .topbar-info {{ width: 100%; justify-content: flex-start; flex-wrap: wrap; gap: 7px 10px; white-space: normal; font-size: 11px; }}
        .topbar-info .desktop-only {{ display: none; }}
        .status-grid-mobile-safe {{ grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }}
        .status-card-mobile-safe {{ padding: 10px 11px; min-height: 86px; }}
        .status-value {{ font-size: 24px; }}
        .status-midvalue {{ font-size: 18px; }}
    }}
</style>

<div class="topbar-mobile-safe">
    <div class="topbar-title">🏦 {name} ({stock_code}) <span style="color:#facc15;">★</span></div>
    <div class="topbar-info">
        <span>◎ {source_text} {time_text}</span>
        <span><span class="topbar-dot"></span>{connection_status}</span>
        <span class="desktop-only">⚙ 設定</span>
        <span class="desktop-only">🔔 聲音警示</span>
        <span class="desktop-only">自訂布局</span>
    </div>
</div>

<div class="status-grid-mobile-safe">
    <div class="status-card-mobile-safe"><div class="status-label">現價</div><div class="status-value" style="color:{UP_COLOR};">{price:.2f}</div><div class="status-sub">即時價</div></div>
    <div class="status-card-mobile-safe"><div class="status-label">AI信心</div><div class="status-value" style="color:#38bdf8;">{score}%</div><div class="status-bar"><div class="status-bar-fill" style="width:{score}%; background:#22c55e;"></div></div></div>
    <div class="status-card-mobile-safe"><div class="status-label">反彈機率</div><div class="status-value" style="color:{rebound_color};">{rebound}%</div><div class="status-sub">偏多反彈</div></div>
    <div class="status-card-mobile-safe"><div class="status-label">主力動向</div><div class="status-midvalue" style="color:{force_color};">{force_title}</div><div class="status-sub">{force_sub}</div></div>
    <div class="status-card-mobile-safe"><div class="status-label">風險等級</div><div class="status-midvalue" style="color:{risk_color};">{risk_title}</div><div class="status-sub">{risk_sub}</div></div>
    <div class="status-card-mobile-safe"><div class="status-label">狀態</div><div class="status-midvalue" style="color:{status_color};">{status_title}</div><div class="status-sub">{status_sub}</div></div>
</div>
'''
    render_html(html, height=160)
