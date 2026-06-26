import random


class SimulationEngine:

    def __init__(

        self,

        mode="一般波動",

        base_price=100,

    ):

        self.mode = mode

        self.base_price = base_price

    # =========================
    # 建立最佳五檔
    # =========================

    def _best5(

        self,

        price,

    ):

        bids = []

        asks = []

        for i in range(5):

            bids.append(

                {

                    "price": round(

                        price - 0.1 * (i + 1),

                        2,

                    ),

                    "size": random.randint(

                        20,

                        300,

                    ),

                }

            )

            asks.append(

                {

                    "price": round(

                        price + 0.1 * (i + 1),

                        2,

                    ),

                    "size": random.randint(

                        20,

                        300,

                    ),

                }

            )

        return bids, asks

    # =========================
    # 產生行情
    # =========================

    def generate(

        self,

        tick,

        total_ticks,

    ):

        # =========================
        # 一般波動
        # =========================

        if self.mode == "一般波動":

            change = random.uniform(

                -0.4,

                0.4,

            )

        # =========================
        # 主力吸籌
        # =========================

        elif self.mode == "主力吸籌":

            if tick < total_ticks * 0.7:

                change = random.uniform(

                    -0.1,

                    0.15,

                )

            else:

                change = random.uniform(

                    0.3,

                    1.2,

                )

        # =========================
        # 洗盤
        # =========================

        elif self.mode == "洗盤":

            if tick % 6 < 3:

                change = random.uniform(

                    -1.2,

                    -0.2,

                )

            else:

                change = random.uniform(

                    0.2,

                    1.2,

                )

        # =========================
        # 突破
        # =========================

        elif self.mode == "突破":

            if tick < total_ticks * 0.5:

                change = random.uniform(

                    -0.2,

                    0.2,

                )

            else:

                change = random.uniform(

                    0.8,

                    2.5,

                )

        # =========================
        # 跌破
        # =========================

        elif self.mode == "跌破":

            if tick < total_ticks * 0.5:

                change = random.uniform(

                    -0.2,

                    0.2,

                )

            else:

                change = random.uniform(

                    -2.5,

                    -0.8,

                )

        # =========================
        # 一般波動
        # =========================

        if self.mode == "一般波動":

            change = random.uniform(

                -0.4,

                0.4,

            )

        # =========================
        # 主力吸籌
        # =========================

        elif self.mode == "主力吸籌":

            if tick < total_ticks * 0.7:

                change = random.uniform(

                    -0.1,

                    0.15,

                )

            else:

                change = random.uniform(

                    0.3,

                    1.2,

                )

        # =========================
        # 洗盤
        # =========================

        elif self.mode == "洗盤":

            if tick % 6 < 3:

                change = random.uniform(

                    -1.2,

                    -0.2,

                )

            else:

                change = random.uniform(

                    0.2,

                    1.2,

                )

        # =========================
        # 突破
        # =========================

        elif self.mode == "突破":

            if tick < total_ticks * 0.5:

                change = random.uniform(

                    -0.2,

                    0.2,

                )

            else:

                change = random.uniform(

                    0.8,

                    2.5,

                )

        # =========================
        # 跌破
        # =========================

        elif self.mode == "跌破":

            if tick < total_ticks * 0.5:

                change = random.uniform(

                    -0.2,

                    0.2,

                )

            else:

                change = random.uniform(

                    -2.5,

                    -0.8,

                )

        # =========================
        # 最新價格
        # =========================

        price = round(

            self.base_price + change,

            2,

        )

        if price <= 1:

            price = 1

        # 下一次價格基準
        self.base_price = price

        # =========================
        # VWAP
        # =========================

        vwap = round(

            price + random.uniform(

                -0.3,

                0.3,

            ),

            2,

        )

        # =========================
        # 成交量
        # =========================

        if self.mode in [

            "突破",

            "軋空行情",

            "拉高出貨",

            "漲停鎖死",

        ]:

            volume = random.randint(

                800,

                3500,

            )

        elif self.mode in [

            "跌破",

            "跳空急跌",

            "跌停鎖死",

        ]:

            volume = random.randint(

                600,

                2800,

            )

        else:

            volume = random.randint(

                20,

                600,

            )

        # =========================
        # Best5
        # =========================

        bids, asks = self._best5(

            price,

        )

        # =========================
        # 主力模式
        # =========================

        if self.mode in [

            "主力吸籌",

            "突破",

            "軋空行情",

            "漲停鎖死",

        ]:

            bids[0]["size"] *= 5

            bids[1]["size"] *= 4

        if self.mode in [

            "拉高出貨",

            "跌破",

            "跳空急跌",

            "跌停鎖死",

        ]:

            asks[0]["size"] *= 5

            asks[1]["size"] *= 4

        # =========================
        # 回傳
        # =========================

        return {

            "name": "Simulation",

            "price": price,

            "vwap": vwap,

            "last_size": volume,

            "bids": bids,

            "asks": asks,

            "trade": {

                "serial": tick,

            },

            "is_close": (

                tick >= total_ticks

            ),

        }

