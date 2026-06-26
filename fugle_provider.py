from fugle_marketdata import RestClient


class FugleProvider:

    def __init__(self, api_key):

        self.client = RestClient(
            api_key=api_key
        )

    def get_quote(
        self,
        symbol,
    ):

        quote = (
            self.client
            .stock
            .intraday
            .quote(
                symbol=symbol
            )
        )

        return {

            "name":
                quote.get(
                    "name",
                    symbol
                ),

            "price":
                quote.get(
                    "lastPrice",
                    0
                ),

            "open":
                quote.get(
                    "openPrice",
                    0
                ),

            "high":
                quote.get(
                    "highPrice",
                    0
                ),

            "low":
                quote.get(
                    "lowPrice",
                    0
                ),

            "vwap":
                quote.get(
                    "avgPrice",
                    0
                ),

            "last_size":
                quote.get(
                    "lastSize",
                    0
                ),

            "bids":
                quote.get(
                    "bids",
                    []
                ),

            "asks":
                quote.get(
                    "asks",
                    []
                ),

            "trade":
                quote.get(
                    "lastTrade",
                    {}
                ),

            "is_close":
                quote.get(
                    "isClose",
                    False
                ),

        }
