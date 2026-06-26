import json
import threading
import time
from websocket import WebSocketApp


class FugleWS:

    def __init__(self, api_key, symbol):
        self.api_key = api_key
        self.symbol = symbol

        self.prices = []
        self.volumes = []
        self.price = 0

        # 🧠 用來判斷 WS 有沒有活著
        self.last_update = 0

    def start(self):

        url = "wss://api.fugle.tw/realtime/v1/channel"

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

        # 👉 auth
        ws.send(json.dumps({
            "event": "auth",
            "data": {
                "apikey": self.api_key
            }
        }))

        # 👉 subscribe
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

        trade = data.get("data", {})

        price = trade.get("price")
        volume = trade.get("size", 1)

        if price is None:
            return

        self.price = price
        self.prices.append(price)
        self.volumes.append(volume)

        # 🧠 更新時間（判斷 WS 活性）
        self.last_update = time.time()

    def on_error(self, ws, error):
        print("WS ERROR:", error)
