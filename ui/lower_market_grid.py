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


def _clamp(value, low=0, high=100):
    return max(low, min(high, value))


def _fmt_price(value):
    value = _safe_float(value)

    if value <= 0:
        return "-"

    return f"{value:.1f}"


def _fmt_size(value):
    value = _safe_float(value)

    if value <= 0:
        return "-"

    if value >= 1000:
        return f"{value / 1000:.1f}K"

    if abs(value - round(value)) < 0.01:
        return str(int(round(value)))

    return f"{value:.1f}"


def _fmt_value(value):
    try:
        return f"{float(value):.2f}"
    except Exception:
        return str(value)


def _normalize(levels):
    rows = []

    for i in range(5):
        if levels and i < len(levels):
            item = levels[i]
        else:
            item = {}

        rows.append(
            {
                "price": _safe_float(item.get("price", 0)),
                "size": _safe_float(item.get("size", 0)),
            }
        )

    return rows


def _avg(values):
    nums = [_safe_float(v) for v in values or [] if _safe_float(v) > 0]

    if not nums:
        return 0

    return sum(nums) / len(nums)


def render_lower_market_grid(
    bids,
    asks,
    decision,
    price,
    vwap,
    ema5,
    ema20,
    rsi,
    macd,
    macd_signal,
    volume,
    volumes,
):

    bids = _normalize(bids)
    asks = _normalize(asks)

    bid_total = sum([b["size"] for b in bids])
    ask_total = sum([a["size"] for a in asks])

    depth_ratio = bid_total / max(ask_total, 1)

    buy_color = DOWN_COLOR
    sell_color = UP_COLOR

    if depth_ratio >= 1.35:
        depth_status = "委買偏強"
        depth_color = buy_color
        depth_desc = "買方掛單支撐較明顯"

    elif depth_ratio <= 0.74:
        depth_status = "委賣偏強"
        depth_color = sell_color
        depth_desc = "賣方掛單壓力較明顯"

    else:
        depth_status = "委買委賣均衡"
        depth_color = WAIT_COLOR
        depth_desc = "買賣雙方暫時拉鋸"

    rows_html = ""

    for i in range(5):
        b = bids[i]
        a = asks[i]

        rows_html += f"""
        <tr>
            <td class="buy-size">{_fmt_size(b["size"])}</td>
            <td class="buy-price">{_fmt_price(b["price"])}</td>
            <td class="sell-price">{_fmt_price(a["price"])}</td>
            <td class="sell-size">{_fmt_size(a["size"])}</td>
        </tr>
        """

    # =========================
    # 多空力道
    # =========================

    long_score = _safe_int(decision.get("long_score", 0))
    short_score = _safe_int(decision.get("short_score", 0))
    bias = _safe_int(decision.get("bias", long_score - short_score))

    force_total = max(long_score + short_score, 1)

    long_pct = _safe_int(long_score / force_total * 100)
    short_pct = 100 - long_pct

    if bias >= 4:
        force_status = "多方優勢"
        force_color = UP_COLOR
        force_desc = "多方條件較完整"

    elif bias <= -4:
        force_status = "空方優勢"
        force_color = DOWN_COLOR
        force_desc = "空方壓力較明顯"

    else:
        force_status = "多空拉鋸"
        force_color = WAIT_COLOR
        force_desc = "等待方向確認"

    # =========================
    # 內外盤估算
    # 目前沒有逐筆內外盤欄位，先用五檔與決策偏向估算。
    # =========================

    pressure = (depth_ratio - 1) * 18 + bias * 3
    outer_pct = _clamp(_safe_int(50 + pressure), 5, 95)
    inner_pct = 100 - outer_pct

    if outer_pct >= 58:
        flow_status = "外盤偏強"
        flow_color = UP_COLOR
        flow_desc = "主動買進力道估算較強"

    elif inner_pct >= 58:
        flow_status = "內盤偏強"
        flow_color = DOWN_COLOR
        flow_desc = "主動賣出壓力估算較強"

    else:
        flow_status = "內外盤平衡"
        flow_color = WAIT_COLOR
        flow_desc = "買賣主動性暫時接近"

    # =========================
    # 技術狀態
    # =========================

    price = _safe_float(price)
    vwap = _safe_float(vwap)
    ema5 = _safe_float(ema5)
    ema20 = _safe_float(ema20)
    rsi = _safe_float(rsi)
    macd = _safe_float(macd)
    macd_signal = _safe_float(macd_signal)
    volume = _safe_float(volume)

    avg_volume = _avg(volumes[-20:]) if volumes else 0

    if price > vwap and ema5 >= ema20:
        trend_status = "多頭上方"
        trend_color = UP_COLOR

    elif price < vwap and ema5 <= ema20:
        trend_status = "空頭下方"
        trend_color = DOWN_COLOR

    else:
        trend_status = "區間震盪"
        trend_color = WAIT_COLOR

    if rsi >= 70:
        rsi_status = "過熱"
        rsi_color = WAIT_COLOR

    elif rsi <= 30:
        rsi_status = "弱勢"
        rsi_color = DOWN_COLOR

    else:
        rsi_status = "中性"
        rsi_color = WAIT_COLOR

    if macd > macd_signal:
        macd_status = "多方轉強"
        macd_color = UP_COLOR

    elif macd < macd_signal:
        macd_status = "空方轉強"
        macd_color = DOWN_COLOR

    else:
        macd_status = "持平"
        macd_color = WAIT_COLOR

    if price > vwap:
        vwap_status = "站上 VWAP"
        vwap_color = UP_COLOR

    elif price < vwap:
        vwap_status = "跌破 VWAP"
        vwap_color = DOWN_COLOR

    else:
        vwap_status = "貼近 VWAP"
        vwap_color = WAIT_COLOR

    if avg_volume > 0 and volume >= avg_volume * 1.5:
        volume_status = "量能放大"
        volume_color = UP_COLOR

    elif avg_volume > 0 and volume <= avg_volume * 0.6:
        volume_status = "量能偏低"
        volume_color = WAIT_COLOR

    else:
        volume_status = "量能正常"
        volume_color = WAIT_COLOR

    # =========================
    # 連次 / 連量
    # =========================

    swing_prediction = decision.get("swing_prediction", {}) or {}
    streak = (
        swing_prediction.get("streak_volume")
        or decision.get("streak_volume")
        or decision.get("signal_quality", {}).get("streak_volume")
        or {}
    )

    streak_available = bool(streak.get("available", False))
    buy_streak_count = _safe_int(streak.get("buy_streak_count", 0))
    sell_streak_count = _safe_int(streak.get("sell_streak_count", 0))
    buy_streak_volume = _safe_float(streak.get("buy_streak_volume", 0))
    sell_streak_volume = _safe_float(streak.get("sell_streak_volume", 0))
    streak_volume_ratio = _safe_float(streak.get("streak_volume_ratio", 1.0), 1.0)
    streak_follow = _safe_float(streak.get("streak_follow_through", 0))
    exhaustion_risk = _safe_float(streak.get("volume_exhaustion_risk", 0))
    absorption_risk = _safe_float(streak.get("absorption_risk", 0))
    last_direction = str(streak.get("last_direction", "FLAT") or "FLAT").upper()

    if not streak_available:
        streak_status = "資料累積中"
        streak_color = WAIT_COLOR
        streak_desc = "需要更多即時 K 線 / 成交流資料，才可判斷連次連量。"
    elif absorption_risk >= 8 or exhaustion_risk >= 8:
        streak_status = "量大未續強"
        streak_color = WAIT_COLOR
        streak_desc = "連量出現但價格推進不足，可能是吸收或末端爆量。"
    elif last_direction == "BUY" and buy_streak_count >= 2 and streak_volume_ratio >= 1.15 and streak_follow >= 0.10:
        streak_status = "買方連量攻擊"
        streak_color = UP_COLOR
        streak_desc = "買方連次與連量同步，且價格有續強跡象。"
    elif last_direction == "SELL" and sell_streak_count >= 2 and streak_volume_ratio >= 1.15 and streak_follow >= 0.10:
        streak_status = "賣方連量攻擊"
        streak_color = DOWN_COLOR
        streak_desc = "賣方連次與連量同步，且價格有續弱跡象。"
    elif last_direction == "BUY" and buy_streak_count >= 2:
        streak_status = "買方連次形成"
        streak_color = UP_COLOR
        streak_desc = "買方連次出現，但仍需觀察連量與續強。"
    elif last_direction == "SELL" and sell_streak_count >= 2:
        streak_status = "賣方連次形成"
        streak_color = DOWN_COLOR
        streak_desc = "賣方連次出現，但仍需觀察連量與續弱。"
    else:
        streak_status = "等待連量"
        streak_color = WAIT_COLOR
        streak_desc = "尚未出現明顯同方向連次連量。"

    streak_bar_pct = _clamp(_safe_int(min(streak_volume_ratio, 2.5) / 2.5 * 100), 0, 100)
    follow_display = f"{streak_follow:.2f}%"
    streak_reason_list = streak.get("reasons", [])
    if isinstance(streak_reason_list, str):
        streak_reason_text = streak_reason_list
    else:
        streak_reason_text = "｜".join([str(x) for x in streak_reason_list[:2]])
    if not streak_reason_text:
        streak_reason_text = streak_desc

    score = _safe_int(decision.get("score", 0))
    rebound = _safe_int(decision.get("rebound", 0))
    rr = _fmt_value(decision.get("rr", "-"))

    st.markdown("### 📊 市場結構")

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

        .grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 9px;
            width: 100%;
            box-sizing: border-box;
        }}

        .card {{
            background: {CARD_BG};
            border: 1px solid {CARD_BORDER};
            border-radius: 14px;
            padding: 10px;
            box-sizing: border-box;
            min-height: 145px;
        }}

        .title-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 7px;
        }}

        .title {{
            color: {TEXT};
            font-size: 13px;
            font-weight: 900;
        }}

        .tag {{
            font-size: 11px;
            font-weight: 900;
            border-radius: 999px;
            padding: 3px 8px;
            border: 1px solid currentColor;
            white-space: nowrap;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            table-layout: fixed;
        }}

        th {{
            color: {SUBTEXT};
            font-size: 10.8px;
            font-weight: 800;
            padding: 4px 3px;
            border-bottom: 1px solid rgba(255,255,255,0.12);
        }}

        td {{
            font-size: 12px;
            font-weight: 900;
            text-align: center;
            padding: 4px 3px;
            border-bottom: 1px solid rgba(255,255,255,0.055);
        }}

        .buy-size,
        .buy-price {{
            color: {buy_color};
        }}

        .sell-price,
        .sell-size {{
            color: {sell_color};
        }}

        .big-status {{
            font-size: 21px;
            font-weight: 900;
            line-height: 1;
            margin-top: 2px;
        }}

        .desc {{
            color: {SUBTEXT};
            font-size: 11.2px;
            margin-top: 5px;
            line-height: 1.35;
        }}

        .bar-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 10px;
            margin-bottom: 6px;
        }}

        .bar-text {{
            font-size: 12px;
            font-weight: 900;
        }}

        .bar {{
            width: 100%;
            height: 12px;
            background: rgba(255,255,255,0.10);
            border-radius: 999px;
            overflow: hidden;
            display: flex;
        }}

        .long-bar {{
            width: {long_pct}%;
            background: {UP_COLOR};
        }}

        .short-bar {{
            width: {short_pct}%;
            background: {DOWN_COLOR};
        }}

        .outer-bar {{
            width: {outer_pct}%;
            background: {UP_COLOR};
        }}

        .inner-bar {{
            width: {inner_pct}%;
            background: {DOWN_COLOR};
        }}

        .streak-bar-fill {{
            width: {streak_bar_pct}%;
            background: {streak_color};
        }}

        .stat-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 6px;
            margin-top: 8px;
        }}

        .stat-grid-2 {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 6px;
            margin-top: 8px;
        }}

        .box {{
            background: rgba(255,255,255,0.035);
            border-radius: 9px;
            padding: 7px 5px;
            text-align: center;
        }}

        .box-label {{
            color: {SUBTEXT};
            font-size: 10.5px;
            margin-bottom: 3px;
        }}

        .box-value {{
            font-size: 13.5px;
            font-weight: 900;
            line-height: 1.15;
        }}

        .tech-row {{
            display: grid;
            grid-template-columns: 1fr auto;
            gap: 8px;
            padding: 5px 0;
            border-bottom: 1px solid rgba(255,255,255,0.06);
            font-size: 11.5px;
        }}

        .tech-name {{
            color: {SUBTEXT};
        }}

        .tech-value {{
            font-weight: 900;
        }}

        @media (max-width: 900px) {{
            .grid {{
                grid-template-columns: 1fr;
                gap: 8px;
            }}

            .card {{
                min-height: auto;
                padding: 10px;
            }}

            .big-status {{
                font-size: 20px;
            }}

            td {{
                font-size: 13px;
                padding: 5px 2px;
            }}
        }}
    </style>
</head>

<body>
    <div class="grid">

        <div class="card">
            <div class="title-row">
                <div class="title">五檔報價</div>
                <div class="tag" style="color:{depth_color};">{depth_status}</div>
            </div>

            <table>
                <thead>
                    <tr>
                        <th>買量</th>
                        <th>買價</th>
                        <th>賣價</th>
                        <th>賣量</th>
                    </tr>
                </thead>

                <tbody>
                    {rows_html}
                </tbody>
            </table>
        </div>

        <div class="card">
            <div class="title-row">
                <div class="title">即時多空力道</div>
                <div class="tag" style="color:{force_color};">{force_status}</div>
            </div>

            <div class="big-status" style="color:{force_color};">{force_status}</div>
            <div class="desc">{force_desc}</div>

            <div class="bar-row">
                <div class="bar-text" style="color:{UP_COLOR};">多方 {long_score}</div>
                <div class="bar-text" style="color:{DOWN_COLOR};">空方 {short_score}</div>
            </div>

            <div class="bar">
                <div class="long-bar"></div>
                <div class="short-bar"></div>
            </div>

            <div class="stat-grid-2">
                <div class="box">
                    <div class="box-label">多空差距</div>
                    <div class="box-value" style="color:{force_color};">{bias}</div>
                </div>

                <div class="box">
                    <div class="box-label">多方占比</div>
                    <div class="box-value" style="color:{UP_COLOR};">{long_pct}%</div>
                </div>
            </div>
        </div>

        <div class="card">
            <div class="title-row">
                <div class="title">內外盤統計</div>
                <div class="tag" style="color:{flow_color};">{flow_status}</div>
            </div>

            <div class="big-status" style="color:{flow_color};">{flow_status}</div>
            <div class="desc">{flow_desc}</div>

            <div class="bar-row">
                <div class="bar-text" style="color:{UP_COLOR};">外盤 {outer_pct}%</div>
                <div class="bar-text" style="color:{DOWN_COLOR};">內盤 {inner_pct}%</div>
            </div>

            <div class="bar">
                <div class="outer-bar"></div>
                <div class="inner-bar"></div>
            </div>

            <div class="stat-grid">
                <div class="box">
                    <div class="box-label">委買</div>
                    <div class="box-value" style="color:{buy_color};">{_fmt_size(bid_total)}</div>
                </div>

                <div class="box">
                    <div class="box-label">買賣比</div>
                    <div class="box-value" style="color:{depth_color};">{depth_ratio:.2f}</div>
                </div>

                <div class="box">
                    <div class="box-label">委賣</div>
                    <div class="box-value" style="color:{sell_color};">{_fmt_size(ask_total)}</div>
                </div>
            </div>
        </div>

        <div class="card">
            <div class="title-row">
                <div class="title">🔥 連次 / 連量</div>
                <div class="tag" style="color:{streak_color};">{streak_status}</div>
            </div>

            <div class="big-status" style="color:{streak_color};">{streak_status}</div>
            <div class="desc">{escape(streak_desc)}</div>

            <div class="bar-row">
                <div class="bar-text" style="color:{UP_COLOR};">買方 {buy_streak_count} 次</div>
                <div class="bar-text" style="color:{DOWN_COLOR};">賣方 {sell_streak_count} 次</div>
            </div>

            <div class="bar">
                <div class="streak-bar-fill"></div>
            </div>

            <div class="stat-grid-2">
                <div class="box">
                    <div class="box-label">連量倍率</div>
                    <div class="box-value" style="color:{streak_color};">{streak_volume_ratio:.2f}x</div>
                </div>

                <div class="box">
                    <div class="box-label">續強 / 續弱</div>
                    <div class="box-value" style="color:{streak_color};">{follow_display}</div>
                </div>
            </div>

            <div class="stat-grid-2">
                <div class="box">
                    <div class="box-label">買方連量</div>
                    <div class="box-value" style="color:{UP_COLOR};">{_fmt_size(buy_streak_volume)}</div>
                </div>

                <div class="box">
                    <div class="box-label">賣方連量</div>
                    <div class="box-value" style="color:{DOWN_COLOR};">{_fmt_size(sell_streak_volume)}</div>
                </div>
            </div>

            <div class="tech-row">
                <div class="tech-name">末端爆量</div>
                <div class="tech-value" style="color:{WAIT_COLOR};">{exhaustion_risk:.1f}</div>
            </div>

            <div class="tech-row">
                <div class="tech-name">吸收風險</div>
                <div class="tech-value" style="color:{WAIT_COLOR};">{absorption_risk:.1f}</div>
            </div>

            <div class="desc">{escape(streak_reason_text)}</div>
        </div>

        <div class="card">
            <div class="title-row">
                <div class="title">籌碼技術狀態</div>
                <div class="tag" style="color:{trend_color};">{trend_status}</div>
            </div>

            <div class="tech-row">
                <div class="tech-name">趨勢方向</div>
                <div class="tech-value" style="color:{trend_color};">{trend_status}</div>
            </div>

            <div class="tech-row">
                <div class="tech-name">RSI</div>
                <div class="tech-value" style="color:{rsi_color};">{rsi:.1f}｜{rsi_status}</div>
            </div>

            <div class="tech-row">
                <div class="tech-name">MACD</div>
                <div class="tech-value" style="color:{macd_color};">{macd_status}</div>
            </div>

            <div class="tech-row">
                <div class="tech-name">VWAP</div>
                <div class="tech-value" style="color:{vwap_color};">{vwap_status}</div>
            </div>

            <div class="tech-row">
                <div class="tech-name">量能</div>
                <div class="tech-value" style="color:{volume_color};">{volume_status}</div>
            </div>

            <div class="stat-grid-2">
                <div class="box">
                    <div class="box-label">Score</div>
                    <div class="box-value" style="color:{trend_color};">{score}</div>
                </div>

                <div class="box">
                    <div class="box-label">反彈率 / RR</div>
                    <div class="box-value" style="color:{WAIT_COLOR};">{rebound}% / {escape(rr)}</div>
                </div>
            </div>
        </div>

    </div>
</body>
</html>
"""

    render_height = 1080 if st.session_state.get("mobile_layout", False) else 790
    render_html(html, height=render_height)
