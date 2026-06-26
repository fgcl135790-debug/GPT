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

        url = f"wss://api.fugle.tw/streaming"

        self.ws = WebSocketApp(
            url,
            on_message=self.on_message,
            on_open=self.on_open
        )

        t = threading.Thread(target=self.ws.run_forever)
        t.daemon = True
        t.start()

    def on_open(self, ws):
        print("WS connected")

        subscribe_msg = {
            "action": "subscribe",
            "symbols": [self.symbol],
            "token": self.api_key
        }

        ws.send(json.dumps(subscribe_msg))

    def on_message(self, ws, message):

        print("RAW MESSAGE:", message)

        data = json.loads(message)

        print("RAW:", data)  # 🔥 你一定要看到這個

        price = data.get("lastPrice") or data.get("price")

        if not price:
            return

        self.price = price
        self.prices.append(price)

        vol = data.get("volume", 1)
        self.volumes.append(vol)
