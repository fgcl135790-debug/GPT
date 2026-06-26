import json
import threading
from websocket import WebSocketApp

class FugleWS:

    def __init__(self, api_key, symbol):
        self.api_key = api_key
        self.symbol = symbol

        self.prices = []
        self.volumes = []
        self.price = 0

    def start(self):

        url = f"wss://api.fugle.tw/realtime/v0.3/stocks?apiKey={self.api_key}"

        self.ws = WebSocketApp(
            url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error
        )

        t = threading.Thread(target=self.ws.run_forever)
        t.daemon = True
        t.start()

    def on_open(self, ws):
        print("WS connected")

        msg = {
            "op": "subscribe",
            "channel": "trades",
            "symbol": self.symbol
        }

        ws.send(json.dumps(msg))
        print("subscribe sent:", msg)

    def on_message(self, ws, message):

        print("RAW:", message)

        data = json.loads(message)

        trade = data.get("data") or {}

        price = trade.get("price")

        if price is None:
            return

        self.price = price
        self.prices.append(price)

        self.volumes.append(trade.get("volume", 1))

    def on_error(self, ws, error):
        print("WS ERROR:", error)
