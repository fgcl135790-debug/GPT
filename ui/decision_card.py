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


def _safe_int(value, default=50):
    try:
        return int(round(float(value)))
    except Exception:
        return default


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def _fmt_size(value):
    v = _safe_float(value, 0.0)
    if abs(v) >= 1000:
        return f"{v / 1000:.1f}K"
    return f"{v:.0f}"


def _fmt(value):
    if value is None:
        return "-"

    try:
        if isinstance(value, (int, float)):
            return f"{value:.2f}"
    except Exception:
        pass

    return str(value)


def render_decision_card(decision):

    action = decision.get("action", "WAIT")
    score = _safe_int(decision.get("score", 50))
    score = max(0, min(100, score))

    entry = escape(_fmt(decision.get("entry", decision.get("entry_price", "-"))))
    stop = escape(_fmt(decision.get("stop_loss", "-")))
    target = escape(_fmt(decision.get("take_profit", "-")))
    rr = escape(_fmt(decision.get("rr", decision.get("risk_reward", "-"))))

    expected_value = decision.get("expected_value", None)
    predicted_win_rate = decision.get("predicted_win_rate", None)
    required_win_rate = decision.get("required_win_rate", None)

    reasons = decision.get("reasons", [])

    # =========================
    # 多週期共振資料
    # =========================

    multi_period = decision.get("multi_period", {}) or {}

    multi_status = (
        decision.get("multi_period_status")
        or multi_period.get("status")
        or "尚未判斷"
    )

    resonance = multi_period.get("resonance", "WAIT")
    multi_confidence = _safe_int(multi_period.get("confidence", 0), 0)
    bull_count = _safe_int(multi_period.get("bull_count", 0), 0)
    bear_count = _safe_int(multi_period.get("bear_count", 0), 0)
    wait_count = _safe_int(multi_period.get("wait_count", 0), 0)

    if resonance in ["BULL_STRONG", "BULL"]:
        multi_color = UP_COLOR
        multi_desc = "多週期結構偏多，做多訊號可信度提高。"

    elif resonance in ["BEAR_STRONG", "BEAR"]:
        multi_color = DOWN_COLOR
        multi_desc = "多週期結構偏空，做空訊號可信度提高。"

    elif resonance == "DIVERGENCE":
        multi_color = WAIT_COLOR
        multi_desc = "多週期方向不一致，容易震盪或假突破。"

    else:
        multi_color = WAIT_COLOR
        multi_desc = "三週期尚未形成明確共振，等待方向確認。"

    # =========================
    # 台股顏色
    # =========================

    if action == "BUY":
        color = UP_COLOR
        title = "可當沖做多"
        badge = "BUY"
        desc = "多方策略成立，等待理想進場區。"

    elif action == "SELL":
        color = DOWN_COLOR
        title = "可當沖做空"
        badge = "SELL"
        desc = "空方條件成立，避免追空等待反彈。"

    else:
        color = WAIT_COLOR
        title = "等待進場"
        badge = "WAIT"
        desc = "多空條件尚未同步，暫時觀望。"

    title = escape(title)
    badge = escape(badge)
    desc = escape(desc)
    multi_status = escape(str(multi_status))
    multi_desc = escape(str(multi_desc))

    # =========================
    # 連次 / 連量顯示資料
    # =========================

    swing_prediction = decision.get("swing_prediction", {}) or {}
    signal_quality = decision.get("signal_quality", {}) or {}
    streak = (
        decision.get("streak_volume")
        or swing_prediction.get("streak_volume")
        or signal_quality.get("streak_volume")
        or {}
    )

    threshold = _safe_int(st.session_state.get("streak_highlight_threshold", 3), 3)
    threshold = max(2, min(10, threshold))

    streak_available = bool(streak.get("available", False))
    buy_streak_count = _safe_int(streak.get("buy_streak_count", 0), 0)
    sell_streak_count = _safe_int(streak.get("sell_streak_count", 0), 0)
    buy_streak_volume = _safe_float(streak.get("buy_streak_volume", 0), 0.0)
    sell_streak_volume = _safe_float(streak.get("sell_streak_volume", 0), 0.0)
    streak_volume_ratio = _safe_float(streak.get("streak_volume_ratio", 1.0), 1.0)
    streak_follow = _safe_float(streak.get("streak_follow_through", 0), 0.0)
    volume_exhaustion_risk = _safe_float(streak.get("volume_exhaustion_risk", 0), 0.0)
    absorption_risk = _safe_float(streak.get("absorption_risk", 0), 0.0)
    last_direction = str(streak.get("last_direction", "FLAT") or "FLAT").upper()

    buy_hit = streak_available and buy_streak_count >= threshold
    sell_hit = streak_available and sell_streak_count >= threshold

    if not streak_available:
        streak_title = "連次資料累積中"
        streak_color = WAIT_COLOR
        streak_desc = "需要更多即時 K 線 / WebSocket 成交流資料。"
        streak_border = "rgba(255,255,255,0.10)"
    elif buy_hit and buy_streak_count >= sell_streak_count:
        streak_title = f"買方連次達標 {buy_streak_count} 次"
        streak_color = UP_COLOR
        streak_desc = "買方連次達到高亮門檻，若價格續強且未追高，做多條件加分。"
        streak_border = UP_COLOR
    elif sell_hit:
        streak_title = f"賣方連次達標 {sell_streak_count} 次"
        streak_color = DOWN_COLOR
        streak_desc = "賣方連次達到高亮門檻，若價格續弱且未追空，做空條件加分。"
        streak_border = DOWN_COLOR
    elif last_direction == "BUY" and buy_streak_count > sell_streak_count:
        streak_title = "買方連次形成"
        streak_color = UP_COLOR
        streak_desc = "買方連次出現，但尚未達到高亮門檻。"
        streak_border = "rgba(255,255,255,0.10)"
    elif last_direction == "SELL" and sell_streak_count > buy_streak_count:
        streak_title = "賣方連次形成"
        streak_color = DOWN_COLOR
        streak_desc = "賣方連次出現，但尚未達到高亮門檻。"
        streak_border = "rgba(255,255,255,0.10)"
    else:
        streak_title = "等待連次連量"
        streak_color = WAIT_COLOR
        streak_desc = "尚未出現明確同方向連續攻擊。"
        streak_border = "rgba(255,255,255,0.10)"

    if volume_exhaustion_risk >= 8 or absorption_risk >= 8:
        streak_desc += " 但目前有末端爆量或吸收風險，不宜只因連次追價。"

    streak_reasons = streak.get("reasons", [])
    if isinstance(streak_reasons, str):
        streak_reason_text = streak_reasons
    elif streak_reasons:
        streak_reason_text = "｜".join([str(x) for x in streak_reasons[:2]])
    else:
        streak_reason_text = streak_desc

    streak_title = escape(str(streak_title))
    streak_desc = escape(str(streak_desc))
    streak_reason_text = escape(str(streak_reason_text))

    degree = int(score * 3.6)

    # =========================
    # 只顯示前三條重點
    # =========================

    top_reasons = reasons[:3]
    more_reasons = reasons[3:]

    reason_items = ""

    if top_reasons:

        for r in top_reasons:
            reason_items += f"""
            <div class="reason-row">
                <span class="reason-dot">◆</span>
                <span>{escape(str(r))}</span>
            </div>
            """

    else:

        reason_items = """
        <div class="reason-row">
            <span class="reason-dot">◆</span>
            <span>目前無明確判斷依據</span>
        </div>
        """

    more_hint = ""

    if more_reasons:

        more_hint = f"""
        <div class="more-hint">
            另有 {len(more_reasons)} 條判斷依據已收合
        </div>
        """

    st.markdown("### 🎯 交易決策")

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
            overflow: visible;
        }}

        .card {{
            background: linear-gradient(135deg, rgba(17,24,39,0.98), rgba(9,14,24,0.98));
            border: 1px solid {CARD_BORDER};
            border-radius: 15px;
            padding: 13px;
            box-sizing: border-box;
            width: 100%;
        }}

        .top {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 10px;
        }}

        .label {{
            color: {SUBTEXT};
            font-size: 12px;
            margin-bottom: 4px;
        }}

        .title {{
            color: {color};
            font-size: 27px;
            font-weight: 900;
            line-height: 1.05;
        }}

        .badge {{
            color: {color};
            border: 1px solid {color};
            background: rgba(255,255,255,0.035);
            padding: 4px 9px;
            border-radius: 999px;
            font-size: 11px;
            font-weight: 900;
            white-space: nowrap;
        }}

        .main {{
            display: grid;
            grid-template-columns: 1fr 88px;
            gap: 12px;
            align-items: center;
        }}

        .rows {{
            border-top: 1px solid rgba(255,255,255,0.08);
            padding-top: 9px;
        }}

        .row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 6px;
            font-size: 12.5px;
        }}

        .k {{
            color: {SUBTEXT};
            font-weight: 700;
        }}

        .v {{
            color: {TEXT};
            font-weight: 900;
            text-align: right;
        }}

        .rr {{
            color: {color};
        }}

        .score-ring {{
            width: 82px;
            height: 82px;
            border-radius: 50%;
            background:
                conic-gradient(
                    {color} 0deg,
                    {color} {degree}deg,
                    rgba(255,255,255,0.10) {degree}deg,
                    rgba(255,255,255,0.10) 360deg
                );
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .score-inner {{
            width: 61px;
            height: 61px;
            border-radius: 50%;
            background: #0b111c;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            border: 1px solid rgba(255,255,255,0.06);
        }}

        .score {{
            font-size: 23px;
            font-weight: 900;
            color: #ffffff;
            line-height: 1;
        }}

        .score-unit {{
            font-size: 10px;
            color: {SUBTEXT};
            margin-top: 2px;
        }}

        .desc {{
            margin-top: 9px;
            padding: 8px 9px;
            border-radius: 10px;
            background: rgba(255,255,255,0.035);
            border-left: 4px solid {color};
            color: {SUBTEXT};
            font-size: 11.5px;
            line-height: 1.4;
        }}

        .multi {{
            margin-top: 9px;
            padding: 9px;
            border-radius: 11px;
            background: rgba(255,255,255,0.035);
            border-left: 4px solid {multi_color};
        }}

        .multi-top {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 6px;
        }}

        .multi-title {{
            color: {multi_color};
            font-size: 14px;
            font-weight: 900;
        }}

        .multi-score {{
            color: {multi_color};
            border: 1px solid {multi_color};
            border-radius: 999px;
            padding: 3px 8px;
            font-size: 11px;
            font-weight: 900;
            white-space: nowrap;
        }}

        .multi-desc {{
            color: {SUBTEXT};
            font-size: 11.2px;
            line-height: 1.35;
            margin-bottom: 7px;
        }}

        .multi-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 6px;
        }}

        .mini-box {{
            background: rgba(255,255,255,0.035);
            border-radius: 8px;
            padding: 6px 4px;
            text-align: center;
        }}

        .mini-label {{
            color: {SUBTEXT};
            font-size: 10px;
            margin-bottom: 2px;
        }}

        .mini-value {{
            font-size: 13px;
            font-weight: 900;
            color: {TEXT};
        }}

        .streak-card {{
            margin-top: 9px;
            padding: 9px;
            border-radius: 11px;
            background: rgba(255,255,255,0.035);
            border: 1px solid {streak_border};
            box-shadow: 0 0 0 1px rgba(255,255,255,0.02) inset;
        }}

        .streak-card.hit {{
            box-shadow: 0 0 0 1px {streak_border} inset, 0 0 14px rgba(255,255,255,0.05);
        }}

        .streak-top {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 8px;
            margin-bottom: 6px;
        }}

        .streak-title {{
            color: {streak_color};
            font-size: 13px;
            font-weight: 900;
            line-height: 1.25;
        }}

        .streak-badge {{
            color: {streak_color};
            border: 1px solid {streak_color};
            border-radius: 999px;
            padding: 3px 8px;
            font-size: 10.5px;
            font-weight: 900;
            white-space: nowrap;
        }}

        .streak-grid {{
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 6px;
            margin-top: 8px;
        }}

        .streak-box {{
            background: rgba(255,255,255,0.035);
            border-radius: 8px;
            padding: 6px 4px;
            text-align: center;
        }}

        .streak-label {{
            color: {SUBTEXT};
            font-size: 10px;
            margin-bottom: 2px;
        }}

        .streak-value {{
            color: {TEXT};
            font-size: 12px;
            font-weight: 900;
        }}

        .streak-desc {{
            margin-top: 7px;
            color: {SUBTEXT};
            font-size: 11px;
            line-height: 1.35;
        }}

        .reason-card {{
            margin-top: 10px;
            border-top: 1px solid rgba(255,255,255,0.08);
            padding-top: 9px;
        }}

        .reason-title {{
            color: {TEXT};
            font-size: 12.5px;
            font-weight: 900;
            margin-bottom: 6px;
        }}

        .reason-row {{
            display: flex;
            gap: 7px;
            align-items: flex-start;
            color: {TEXT};
            font-size: 11.8px;
            line-height: 1.35;
            margin-bottom: 4px;
        }}

        .reason-dot {{
            color: #60a5fa;
            font-size: 10px;
            margin-top: 2px;
        }}

        .more-hint {{
            margin-top: 6px;
            color: {SUBTEXT};
            font-size: 11px;
            text-align: right;
        }}

        @media (max-width: 760px) {{
            .card {{ padding: 12px; }}
            .title {{ font-size: 23px; }}
            .main {{ grid-template-columns: 1fr; gap: 10px; }}
            .score-ring {{ width: 72px; height: 72px; margin: 0 auto; }}
            .score-inner {{ width: 54px; height: 54px; }}
            .multi-grid {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
            .streak-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
        }}

    </style>
</head>

<body>
    <div class="card">

        <div class="top">
            <div>
                <div class="label">建議策略</div>
                <div class="title">{title}</div>
            </div>

            <div class="badge">{badge}</div>
        </div>

        <div class="main">

            <div class="rows">

                <div class="row">
                    <div class="k">進場區間</div>
                    <div class="v">{entry}</div>
                </div>

                <div class="row">
                    <div class="k">停損價位</div>
                    <div class="v">{stop}</div>
                </div>

                <div class="row">
                    <div class="k">停利目標</div>
                    <div class="v">{target}</div>
                </div>

                <div class="row">
                    <div class="k">風險報酬比</div>
                    <div class="v rr">{rr}</div>
                </div>

                <div class="row">
                    <div class="k">扣成本期望</div>
                    <div class="v rr">{escape(_fmt(expected_value))}%</div>
                </div>

                <div class="row">
                    <div class="k">預測勝率 / 需求</div>
                    <div class="v">{escape(_fmt(predicted_win_rate))}% / {escape(_fmt(required_win_rate))}%</div>
                </div>

            </div>

            <div class="score-ring">
                <div class="score-inner">
                    <div class="score">{score}</div>
                    <div class="score-unit">/100</div>
                </div>
            </div>

        </div>

        <div class="desc">
            {desc}
        </div>

        <div class="multi">
            <div class="multi-top">
                <div class="multi-title">🔀 {multi_status}</div>
                <div class="multi-score">共振 {multi_confidence}</div>
            </div>

            <div class="multi-desc">{multi_desc}</div>

            <div class="multi-grid">
                <div class="mini-box">
                    <div class="mini-label">多頭週期</div>
                    <div class="mini-value" style="color:{UP_COLOR};">{bull_count}</div>
                </div>

                <div class="mini-box">
                    <div class="mini-label">空頭週期</div>
                    <div class="mini-value" style="color:{DOWN_COLOR};">{bear_count}</div>
                </div>

                <div class="mini-box">
                    <div class="mini-label">觀望週期</div>
                    <div class="mini-value" style="color:{WAIT_COLOR};">{wait_count}</div>
                </div>
            </div>
        </div>

        <div class="streak-card {'hit' if (buy_hit or sell_hit) else ''}">
            <div class="streak-top">
                <div class="streak-title">🔥 {streak_title}</div>
                <div class="streak-badge">門檻 {threshold} 次</div>
            </div>

            <div class="streak-grid">
                <div class="streak-box">
                    <div class="streak-label">買方連次</div>
                    <div class="streak-value" style="color:{UP_COLOR};">{buy_streak_count}</div>
                </div>
                <div class="streak-box">
                    <div class="streak-label">賣方連次</div>
                    <div class="streak-value" style="color:{DOWN_COLOR};">{sell_streak_count}</div>
                </div>
                <div class="streak-box">
                    <div class="streak-label">連量倍率</div>
                    <div class="streak-value" style="color:{streak_color};">{streak_volume_ratio:.2f}x</div>
                </div>
                <div class="streak-box">
                    <div class="streak-label">續強/續弱</div>
                    <div class="streak-value" style="color:{streak_color};">{streak_follow:.2f}%</div>
                </div>
                <div class="streak-box">
                    <div class="streak-label">買方連量</div>
                    <div class="streak-value" style="color:{UP_COLOR};">{escape(_fmt_size(buy_streak_volume))}</div>
                </div>
                <div class="streak-box">
                    <div class="streak-label">賣方連量</div>
                    <div class="streak-value" style="color:{DOWN_COLOR};">{escape(_fmt_size(sell_streak_volume))}</div>
                </div>
                <div class="streak-box">
                    <div class="streak-label">末端爆量</div>
                    <div class="streak-value" style="color:{WAIT_COLOR if volume_exhaustion_risk >= 8 else TEXT};">{volume_exhaustion_risk:.0f}</div>
                </div>
                <div class="streak-box">
                    <div class="streak-label">吸收風險</div>
                    <div class="streak-value" style="color:{WAIT_COLOR if absorption_risk >= 8 else TEXT};">{absorption_risk:.0f}</div>
                </div>
            </div>

            <div class="streak-desc">{streak_reason_text}</div>
        </div>

        <div class="reason-card">
            <div class="reason-title">重點依據</div>
            {reason_items}
            {more_hint}
        </div>

    </div>
</body>
</html>
"""

    render_html(html, height=760)
