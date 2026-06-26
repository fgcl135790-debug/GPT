import json
import threading
from websocket import WebSocketApp

class FugleWS:

    def __init__(self, api_key, symbol):

        self.api_key = api_key
        self.symbol = symbol

        self.prices = []
        self.volumes = []
        self.price = None

    def start(self):

        url = "wss://api.fugle.tw/streaming"

        self.ws = WebSocketApp(
            url,
            on_open=self.on_open,
            on_message=self.on_message
        )

        t = threading.Thread(target=self.ws.run_forever)
        t.daemon = True
        t.start()

    def on_open(self, ws):
        print("WS connected")

        msg = {
            "action": "subscribe",
            "symbols": [self.symbol],
            "token": self.api_key
        }

        ws.send(json.dumps(msg))

    def on_message(self, ws, message):
        print("RAW WS:", message)

        try:
            data = json.loads(message)
            print("WS RAW:", data)

            # 🔥 多種 fallback key（Fugle 很亂）
            price = (
                data.get("lastPrice") or
                data.get("price") or
                data.get("tradePrice")
            )

            if price is None:
                return

            self.price = float(price)
            self.prices.append(self.price)

            vol = data.get("volume") or 1
            self.volumes.append(vol)

        except Exception as e:
            print("WS ERROR:", e)
