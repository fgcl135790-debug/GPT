from simulation_engine import SimulationEngine
from fugle_provider import FugleProvider


def get_market_data(
    data_source,
    api_key=None,
    stock_code="2330",
    tick=0,
    mode="一般波動",
    sim_run_id=0,
):
    """
    統一資料入口：
    - 真實盤：Fugle REST
    - 模擬盤：SimulationEngine 開盤到收盤回放
    """

    if data_source == "模擬盤":
        return SimulationEngine.get_quote(
            stock_code=stock_code,
            tick=tick,
            scenario=mode or "一般波動",
            sim_run_id=sim_run_id,
        )

    if data_source == "真實盤":
        if not api_key:
            raise ValueError("missing api_key")

        provider = FugleProvider(api_key)
        return provider.get_quote(stock_code)

    raise ValueError(f"unknown data_source: {data_source}")
