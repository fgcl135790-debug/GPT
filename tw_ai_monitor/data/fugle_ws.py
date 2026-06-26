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

        url = "wss://api.fugle.tw/marketdata/v1.0/stock/streaming"

        self.ws = WebSocketApp(
            url,
            on_open=self.on_open,
            on_message=self.on_message,
        )

        t = threading.Thread(target=self.ws.run_forever)
        t.daemon = True
        t.start()

    def on_open(self, ws):
        print("WS connected")

        # 1. auth
        ws.send(json.dumps({
            "event": "auth",
            "data": {
                "apikey": self.api_key
            }
        }))

        # 2. subscribe
        ws.send(json.dumps({
            "event": "subscribe",
            "data": {
                "channel": "trades",
                "symbol": self.symbol
            }
        }))

    def on_message(self, ws, message):

        print("RAW:", message)

        data = json.loads(message)

        payload = data.get("data", {})

        price = payload.get("lastPrice")
        if price is None:
            return

        self.price = price
        self.prices.append(price)

        vol = payload.get("lastSize", 1)
        self.volumes.append(vol)
