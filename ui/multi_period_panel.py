import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime
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


def _to_datetime(value):
    if isinstance(value, datetime):
        return value

    try:
        return datetime.fromisoformat(str(value))
    except Exception:
        return None


def _ema(values, span):
    nums = [_safe_float(v) for v in values]

    if not nums:
        return []

    alpha = 2 / (span + 1)
    result = [nums[0]]

    for v in nums[1:]:
        result.append(alpha * v + (1 - alpha) * result[-1])

    return result


def _period_minutes(period):
    mapping = {
        "1分": 1,
        "5分": 5,
        "15分": 15,
    }

    return mapping.get(period, 1)


def _bucket_time(dt, minutes):
    if dt is None:
        return None

    minute = (dt.minute // minutes) * minutes

    return dt.replace(
        minute=minute,
        second=0,
        microsecond=0,
    )


def _prepare_ticks(prices, volumes, vwaps, times):
    clean = []

    for i, price in enumerate(prices or []):
        p = _safe_float(price)

        if p <= 0:
            continue

        v = _safe_float(volumes[i]) if i < len(volumes or []) else 0
        w = _safe_float(vwaps[i]) if i < len(vwaps or []) else p
        t = _to_datetime(times[i]) if i < len(times or []) else None

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


def _aggregate_period(prices, volumes, vwaps, times, period):
    clean = _prepare_ticks(prices, volumes, vwaps, times)

    if not clean:
        return {
            "prices": [],
            "volumes": [],
            "vwaps": [],
        }

    if period == "1分":
        return {
            "prices": [item["price"] for item in clean],
            "volumes": [item["volume"] for item in clean],
            "vwaps": [item["vwap"] for item in clean],
        }

    minutes = _period_minutes(period)
    buckets = {}
    fallback_index = 0

    for item in clean:
        key = _bucket_time(item["time"], minutes)

        if key is None:
            key = f"bucket_{fallback_index // minutes}"
            fallback_index += 1

        if key not in buckets:
            buckets[key] = {
                "prices": [],
                "volumes": [],
                "vwaps": [],
            }

        buckets[key]["prices"].append(item["price"])
        buckets[key]["volumes"].append(item["volume"])
        buckets[key]["vwaps"].append(item["vwap"])

    agg_prices = []
    agg_volumes = []
    agg_vwaps = []

    for key in sorted(buckets.keys(), key=lambda x: str(x)):
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

    return {
        "prices": agg_prices,
        "volumes": agg_volumes,
        "vwaps": agg_vwaps,
    }


def _analyze_period(period, prices, volumes, vwaps, times):
    data = _aggregate_period(
        prices=prices,
        volumes=volumes,
        vwaps=vwaps,
        times=times,
        period=period,
    )

    ps = data["prices"]
    vs = data["volumes"]
    ws = data["vwaps"]

    if not ps:
        return {
            "period": period,
            "status": "資料不足",
            "color": WAIT_COLOR,
            "confidence": 0,
            "long_score": 0,
            "short_score": 0,
            "price": 0,
            "vwap": 0,
            "ema5": 0,
            "ema20": 0,
            "volume_status": "等待資料",
            "structure": "資料不足",
            "desc": "目前資料不足，等待更多即時資料。",
        }

    price = ps[-1]
    prev_price = ps[-2] if len(ps) >= 2 else price

    current_vwap = ws[-1] if ws else price
    if current_vwap <= 0:
        current_vwap = price

    ema5_list = _ema(ps, 5)
    ema20_list = _ema(ps, 20)

    ema5 = ema5_list[-1] if ema5_list else price
    ema20 = ema20_list[-1] if ema20_list else price

    avg_volume = 0

    valid_volumes = [
        _safe_float(v)
        for v in vs[-20:]
        if _safe_float(v) > 0
    ]

    if valid_volumes:
        avg_volume = sum(valid_volumes) / len(valid_volumes)

    current_volume = _safe_float(vs[-1]) if vs else 0

    long_score = 0
    short_score = 0
    notes = []

    if price > current_vwap:
        long_score += 2
        notes.append("價格站上 VWAP")
    elif price < current_vwap:
        short_score += 2
        notes.append("價格跌破 VWAP")

    if ema5 > ema20:
        long_score += 2
        notes.append("EMA5 在 EMA20 之上")
    elif ema5 < ema20:
        short_score += 2
        notes.append("EMA5 在 EMA20 之下")

    if price > prev_price:
        long_score += 1
        notes.append("短線價格上彎")
    elif price < prev_price:
        short_score += 1
        notes.append("短線價格下彎")

    if avg_volume > 0 and current_volume >= avg_volume * 1.35:
        if price >= prev_price:
            long_score += 1
            notes.append("上漲伴隨量能放大")
        else:
            short_score += 1
            notes.append("下跌伴隨量能放大")

    diff = long_score - short_score

    if diff >= 2:
        status = "多頭"
        color = UP_COLOR
        structure = "多方結構"
        desc = "短線多方條件較完整。"

    elif diff <= -2:
        status = "空頭"
        color = DOWN_COLOR
        structure = "空方結構"
        desc = "短線空方壓力較明顯。"

    else:
        status = "盤整"
        color = WAIT_COLOR
        structure = "震盪結構"
        desc = "多空條件尚未一致。"

    confidence = _clamp(
        45 + abs(diff) * 12,
        0,
        95,
    )

    if avg_volume <= 0:
        volume_status = "量能累積中"
    elif current_volume >= avg_volume * 1.5:
        volume_status = "量能放大"
    elif current_volume <= avg_volume * 0.6:
        volume_status = "量能偏低"
    else:
        volume_status = "量能正常"

    return {
        "period": period,
        "status": status,
        "color": color,
        "confidence": confidence,
        "long_score": long_score,
        "short_score": short_score,
        "price": price,
        "vwap": current_vwap,
        "ema5": ema5,
        "ema20": ema20,
        "volume_status": volume_status,
        "structure": structure,
        "desc": desc,
        "notes": notes[:3],
    }


def _card_html(item):
    period = escape(str(item["period"]))
    status = escape(str(item["status"]))
    color = item["color"]
    confidence = _safe_int(item["confidence"])
    long_score = _safe_int(item["long_score"])
    short_score = _safe_int(item["short_score"])
    price = _safe_float(item["price"])
    vwap = _safe_float(item["vwap"])
    ema5 = _safe_float(item["ema5"])
    ema20 = _safe_float(item["ema20"])
    volume_status = escape(str(item["volume_status"]))
    structure = escape(str(item["structure"]))
    desc = escape(str(item["desc"]))

    total = max(long_score + short_score, 1)
    long_pct = _clamp(_safe_int(long_score / total * 100), 0, 100)
    short_pct = 100 - long_pct

    return f"""
    <div class="period-card">
        <div class="period-head">
            <div class="period-name">{period}</div>
            <div class="period-tag" style="color:{color};">{status}</div>
        </div>

        <div class="period-status" style="color:{color};">{structure}</div>
        <div class="period-desc">{desc}</div>

        <div class="bar-row">
            <div style="color:{UP_COLOR};">多方 {long_score}</div>
            <div style="color:{DOWN_COLOR};">空方 {short_score}</div>
        </div>

        <div class="bar">
            <div class="long-bar" style="width:{long_pct}%;"></div>
            <div class="short-bar" style="width:{short_pct}%;"></div>
        </div>

        <div class="mini-grid">
            <div class="box">
                <div class="box-label">信心</div>
                <div class="box-value" style="color:{color};">{confidence}%</div>
            </div>

            <div class="box">
                <div class="box-label">價格</div>
                <div class="box-value">{price:.2f}</div>
            </div>

            <div class="box">
                <div class="box-label">VWAP</div>
                <div class="box-value">{vwap:.2f}</div>
            </div>

            <div class="box">
                <div class="box-label">EMA結構</div>
                <div class="box-value" style="color:{color};">{ema5:.2f}/{ema20:.2f}</div>
            </div>
        </div>

        <div class="volume-note">
            量能：{volume_status}
        </div>
    </div>
    """


def render_multi_period_analysis(prices, volumes, vwap_values, time_values):
    periods = ["1分", "5分", "15分"]

    results = [
        _analyze_period(
            period=period,
            prices=prices,
            volumes=volumes,
            vwaps=vwap_values,
            times=time_values,
        )
        for period in periods
    ]

    statuses = [item["status"] for item in results]

    bull_count = statuses.count("多頭")
    bear_count = statuses.count("空頭")
    flat_count = statuses.count("盤整")

    avg_confidence = _safe_int(
        sum([_safe_float(item["confidence"]) for item in results]) / max(len(results), 1)
    )

    if bull_count == 3:
        resonance_status = "多頭共振"
        resonance_color = UP_COLOR
        resonance_desc = "1分、5分、15分同步偏多，短線多方一致性較高。"

    elif bear_count == 3:
        resonance_status = "空頭共振"
        resonance_color = DOWN_COLOR
        resonance_desc = "1分、5分、15分同步偏空，短線空方一致性較高。"

    elif bull_count >= 2 and bear_count == 0:
        resonance_status = "多方偏強"
        resonance_color = UP_COLOR
        resonance_desc = "多數週期偏多，但仍需確認是否放量延續。"

    elif bear_count >= 2 and bull_count == 0:
        resonance_status = "空方偏強"
        resonance_color = DOWN_COLOR
        resonance_desc = "多數週期偏空，反彈時需留意壓力。"

    elif bull_count >= 1 and bear_count >= 1:
        resonance_status = "多空背離"
        resonance_color = WAIT_COLOR
        resonance_desc = "不同週期方向不一致，容易震盪或假突破。"

    else:
        resonance_status = "盤整觀望"
        resonance_color = WAIT_COLOR
        resonance_desc = "三週期尚未形成共振，等待方向確認。"

    cards_html = ""

    for item in results:
        cards_html += _card_html(item)

    st.markdown("### 🔀 多週期分析")

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
            width: 100%;
            box-sizing: border-box;
        }}

        .summary {{
            background: {CARD_BG};
            border: 1px solid {CARD_BORDER};
            border-radius: 14px;
            padding: 12px;
            box-sizing: border-box;
            margin-bottom: 9px;
        }}

        .summary-top {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 12px;
        }}

        .summary-label {{
            color: {SUBTEXT};
            font-size: 12px;
            margin-bottom: 4px;
        }}

        .summary-status {{
            color: {resonance_color};
            font-size: 26px;
            font-weight: 900;
            line-height: 1;
        }}

        .summary-desc {{
            color: {SUBTEXT};
            font-size: 12px;
            line-height: 1.4;
            margin-top: 6px;
        }}

        .score {{
            border: 1px solid {resonance_color};
            color: {resonance_color};
            border-radius: 999px;
            padding: 5px 10px;
            font-size: 12px;
            font-weight: 900;
            white-space: nowrap;
        }}

        .grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 9px;
        }}

        .period-card {{
            background: {CARD_BG};
            border: 1px solid {CARD_BORDER};
            border-radius: 14px;
            padding: 11px;
            box-sizing: border-box;
            min-height: 210px;
        }}

        .period-head {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }}

        .period-name {{
            color: {TEXT};
            font-size: 14px;
            font-weight: 900;
        }}

        .period-tag {{
            border: 1px solid currentColor;
            border-radius: 999px;
            padding: 3px 8px;
            font-size: 11px;
            font-weight: 900;
        }}

        .period-status {{
            font-size: 20px;
            font-weight: 900;
            line-height: 1;
        }}

        .period-desc {{
            color: {SUBTEXT};
            font-size: 11.5px;
            line-height: 1.35;
            margin-top: 5px;
        }}

        .bar-row {{
            display: flex;
            justify-content: space-between;
            margin-top: 10px;
            margin-bottom: 6px;
            font-size: 12px;
            font-weight: 900;
        }}

        .bar {{
            width: 100%;
            height: 12px;
            border-radius: 999px;
            overflow: hidden;
            background: rgba(255,255,255,0.10);
            display: flex;
        }}

        .long-bar {{
            background: {UP_COLOR};
            height: 100%;
        }}

        .short-bar {{
            background: {DOWN_COLOR};
            height: 100%;
        }}

        .mini-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 6px;
            margin-top: 9px;
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
            color: {TEXT};
            font-size: 13px;
            font-weight: 900;
            line-height: 1.15;
        }}

        .volume-note {{
            margin-top: 8px;
            padding-top: 7px;
            border-top: 1px solid rgba(255,255,255,0.08);
            color: {SUBTEXT};
            font-size: 11px;
        }}

        .explain {{
            margin-top: 9px;
            background: rgba(255,255,255,0.035);
            border-left: 4px solid {resonance_color};
            border-radius: 10px;
            padding: 9px;
            color: {SUBTEXT};
            font-size: 11.5px;
            line-height: 1.45;
        }}

        @media (max-width: 900px) {{
            .grid {{
                grid-template-columns: 1fr;
            }}

            .summary-top {{
                flex-direction: column;
            }}
        }}
    </style>
</head>

<body>
    <div class="wrap">

        <div class="summary">
            <div class="summary-top">
                <div>
                    <div class="summary-label">三週期共振結論</div>
                    <div class="summary-status">{escape(resonance_status)}</div>
                    <div class="summary-desc">{escape(resonance_desc)}</div>
                </div>

                <div class="score">
                    共振分數 {avg_confidence}
                </div>
            </div>
        </div>

        <div class="grid">
            {cards_html}
        </div>

        <div class="explain">
            多週期分析用 1分、5分、15分的 VWAP、EMA 結構、短線方向與量能做共振判斷。
            當三個週期方向一致時，訊號可信度較高；若週期互相矛盾，容易出現震盪或假突破。
        </div>

    </div>
</body>
</html>
"""

    components.html(
        html,
        height=365,
        scrolling=False,
    )
