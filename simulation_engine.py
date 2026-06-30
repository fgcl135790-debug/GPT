import math
import random
from datetime import datetime, timedelta


class SimulationEngine:
    STOCK_BASE = {
        "2330": {
            "name": "台積電",
            "price": 2340.0,
            "tick": 5.0,
            "base_volume": 360,
        },
        "3481": {
            "name": "群創",
            "price": 65.0,
            "tick": 0.05,
            "base_volume": 520,
        },
        "2317": {
            "name": "鴻海",
            "price": 210.0,
            "tick": 0.5,
            "base_volume": 420,
        },
        "2454": {
            "name": "聯發科",
            "price": 1360.0,
            "tick": 5.0,
            "base_volume": 260,
        },
    }

    TOTAL_MINUTES = 271  # 09:00 ~ 13:30

    # 關鍵：快取同一條模擬日內路徑
    # key = stock_code | scenario | sim_run_id
    PATH_CACHE = {}

    @staticmethod
    def _safe_int(value, default=0):
        try:
            return int(value)
        except Exception:
            return default

    @staticmethod
    def _round_to_tick(price, tick_size):
        if tick_size <= 0:
            return round(price, 2)

        return round(round(price / tick_size) * tick_size, 2)

    @staticmethod
    def _stock_profile(stock_code):
        code = str(stock_code)

        if code in SimulationEngine.STOCK_BASE:
            return SimulationEngine.STOCK_BASE[code]

        return {
            "name": code,
            "price": 100.0,
            "tick": 0.1,
            "base_volume": 300,
        }

    @staticmethod
    def _scenario_force(scenario, x):
        if scenario == "漲停鎖死":
            if x < 0.18:
                return 0.55
            return 0.07

        if scenario == "跌停鎖死":
            if x < 0.18:
                return -0.55
            return -0.07

        if scenario == "跳空急跌":
            if x < 0.15:
                return -0.55
            if x < 0.42:
                return -0.18
            if x < 0.70:
                return 0.06
            return -0.03

        if scenario in ["軋空行情", "誘空嘎空"]:
            if x < 0.22:
                return -0.11
            if x < 0.58:
                return 0.25
            return 0.10

        if scenario in ["誘多出貨", "拉高出貨"]:
            if x < 0.35:
                return 0.22
            if x < 0.58:
                return 0.03
            return -0.20

        if scenario == "主力吸籌":
            if x < 0.40:
                return 0.00
            if x < 0.72:
                return 0.06
            return 0.16

        return 0.025 * math.sin(x * math.pi * 5)

    @staticmethod
    def _make_full_day_path(stock_code, scenario, sim_run_id=0):
        """
        產生完整 09:00 ~ 13:30 走勢。
        注意：這裡的 seed 絕對不能包含 tick。
        tick 只能控制目前播放到第幾分鐘。
        """

        profile = SimulationEngine._stock_profile(stock_code)

        name = profile["name"]
        base_price = float(profile["price"])
        tick_size = float(profile["tick"])
        base_volume = float(profile["base_volume"])

        seed = (
            sum(ord(c) for c in str(stock_code))
            + sum(ord(c) for c in str(scenario)) * 13
            + int(sim_run_id) * 101
        )

        rng = random.Random(seed)

        # 固定日期時間，不使用現在的秒數，避免 x 軸每秒改變
        start = datetime(2026, 1, 1, 9, 0, 0)

        open_gap = rng.uniform(-0.006, 0.006)

        if scenario == "跳空急跌":
            open_gap = rng.uniform(-0.025, -0.012)

        elif scenario in ["軋空行情", "誘空嘎空"]:
            open_gap = rng.uniform(-0.012, 0.002)

        elif scenario == "漲停鎖死":
            open_gap = rng.uniform(0.018, 0.035)

        elif scenario == "跌停鎖死":
            open_gap = rng.uniform(-0.035, -0.018)

        last_price = base_price * (1 + open_gap)

        day_high = last_price
        day_low = last_price

        cum_amount = 0.0
        cum_volume = 0.0

        history = []

        for i in range(SimulationEngine.TOTAL_MINUTES):
            x = i / max(SimulationEngine.TOTAL_MINUTES - 1, 1)

            scenario_force = SimulationEngine._scenario_force(
                scenario=scenario,
                x=x,
            )

            morning_wave = math.sin(x * math.pi * 2.8) * 0.055
            intraday_wave = math.sin(x * math.pi * 11.0) * 0.035
            micro_wave = math.sin(x * math.pi * 37.0) * 0.014
            noise = rng.uniform(-0.045, 0.045)

            price_scale = max(base_price * 0.00115, tick_size)

            change = (
                scenario_force
                + morning_wave
                + intraday_wave
                + micro_wave
                + noise
            ) * price_scale

            last_price = last_price + change

            limit_high = base_price * 1.095
            limit_low = base_price * 0.905

            last_price = max(
                limit_low,
                min(limit_high, last_price),
            )

            price = SimulationEngine._round_to_tick(
                last_price,
                tick_size,
            )

            day_high = max(day_high, price)
            day_low = min(day_low, price)

            open_factor = 2.2 if i < 18 else 1.0
            close_factor = 1.5 if i > 235 else 1.0
            wave_volume = 1 + max(0, math.sin(x * math.pi * 5.5)) * 0.75
            volatility_factor = 1 + abs(change) / max(tick_size, 0.01) * 0.26

            spike = 1.0

            if i in [25, 55, 88, 126, 162, 205, 240]:
                spike = rng.uniform(2.0, 4.0)

            volume = (
                base_volume
                * open_factor
                * close_factor
                * wave_volume
                * volatility_factor
                * spike
                * rng.uniform(0.65, 1.35)
            )

            volume = max(8, round(volume, 0))

            cum_amount += price * volume
            cum_volume += volume

            vwap = cum_amount / max(cum_volume, 1)

            history.append(
                {
                    "time": start + timedelta(minutes=i),
                    "price": price,
                    "volume": volume,
                    "vwap": round(vwap, 2),
                    "high": round(day_high, 2),
                    "low": round(day_low, 2),
                }
            )

        return {
            "name": name,
            "base_price": base_price,
            "tick_size": tick_size,
            "base_volume": base_volume,
            "history": history,
            "sim_run_id": sim_run_id,
            "scenario": scenario,
        }

    @staticmethod
    def _get_cached_full_day_path(stock_code, scenario, sim_run_id):
        cache_key = f"{stock_code}|{scenario}|{sim_run_id}"

        if cache_key not in SimulationEngine.PATH_CACHE:
            SimulationEngine.PATH_CACHE[cache_key] = SimulationEngine._make_full_day_path(
                stock_code=stock_code,
                scenario=scenario,
                sim_run_id=sim_run_id,
            )

            # 避免快取無限長大，只保留最近 20 條
            if len(SimulationEngine.PATH_CACHE) > 20:
                oldest_key = list(SimulationEngine.PATH_CACHE.keys())[0]
                SimulationEngine.PATH_CACHE.pop(oldest_key, None)

        return SimulationEngine.PATH_CACHE[cache_key]

    @staticmethod
    def _make_intraday_replay(stock_code, tick=0, scenario="一般波動", sim_run_id=0):
        profile = SimulationEngine._get_cached_full_day_path(
            stock_code=stock_code,
            scenario=scenario,
            sim_run_id=sim_run_id,
        )

        full_history = profile["history"]

        tick = SimulationEngine._safe_int(tick, 0)

        # 一開始 25 筆，之後每次刷新增加 1 分鐘
        reveal_count = min(
            len(full_history),
            max(25, 25 + tick),
        )

        history = full_history[:reveal_count]
        latest = history[-1]

        tick_size = profile["tick_size"]
        base_volume = profile["base_volume"]

        # 五檔可以隨 tick 微變，這不會影響走勢線
        book_seed = (
            sum(ord(c) for c in str(stock_code))
            + tick * 17
            + sum(ord(c) for c in str(scenario)) * 19
            + int(sim_run_id) * 97
        )

        rng = random.Random(book_seed)

        bid_bias = 1.0
        ask_bias = 1.0

        if latest["price"] >= latest["vwap"]:
            bid_bias = 1.24
            ask_bias = 0.92
        else:
            bid_bias = 0.92
            ask_bias = 1.24

        bids = []
        asks = []

        for level in range(5):
            step = tick_size * (level + 1)

            bid_price = SimulationEngine._round_to_tick(
                latest["price"] - step,
                tick_size,
            )

            ask_price = SimulationEngine._round_to_tick(
                latest["price"] + step,
                tick_size,
            )

            bid_size = round(
                base_volume * bid_bias * rng.uniform(0.55, 1.65),
                0,
            )

            ask_size = round(
                base_volume * ask_bias * rng.uniform(0.55, 1.65),
                0,
            )

            bids.append(
                {
                    "price": bid_price,
                    "size": bid_size,
                }
            )

            asks.append(
                {
                    "price": ask_price,
                    "size": ask_size,
                }
            )

        serial = f"SIM_{stock_code}_{scenario}_{sim_run_id}_{tick}_{reveal_count}"

        return {
            "name": profile["name"],
            "stock_code": str(stock_code),
            "price": latest["price"],
            "vwap": latest["vwap"],
            "avgPrice": latest["vwap"],
            "last_size": latest["volume"],
            "lastSize": latest["volume"],
            "volume": latest["volume"],
            "high": latest["high"],
            "low": latest["low"],
            "bids": bids,
            "asks": asks,
            "trade": {
                "serial": serial,
                "time": latest["time"].isoformat(),
                "price": latest["price"],
                "size": latest["volume"],
            },
            "serial": serial,
            "history": history,
            "full_day_points": len(full_history),
            "replay_points": reveal_count,
            "scenario": scenario,
            "sim_run_id": sim_run_id,
        }

    @staticmethod
    def get_quote(stock_code="2330", tick=0, scenario="一般波動", sim_run_id=0, **kwargs):
        return SimulationEngine._make_intraday_replay(
            stock_code=stock_code,
            tick=tick,
            scenario=scenario or "一般波動",
            sim_run_id=sim_run_id,
        )

    @staticmethod
    def generate(stock_code="2330", tick=0, scenario="一般波動", sim_run_id=0, **kwargs):
        return SimulationEngine.get_quote(
            stock_code=stock_code,
            tick=tick,
            scenario=scenario,
            sim_run_id=sim_run_id,
        )

    @staticmethod
    def get_market_data(stock_code="2330", tick=0, scenario="一般波動", sim_run_id=0, **kwargs):
        return SimulationEngine.get_quote(
            stock_code=stock_code,
            tick=tick,
            scenario=scenario,
            sim_run_id=sim_run_id,
        )

    @staticmethod
    def next_quote(stock_code="2330", tick=0, scenario="一般波動", sim_run_id=0, **kwargs):
        return SimulationEngine.get_quote(
            stock_code=stock_code,
            tick=tick,
            scenario=scenario,
            sim_run_id=sim_run_id,
        )
