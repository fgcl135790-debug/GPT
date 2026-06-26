import websocket
import json
import threading

class FugleWS:

    def __init__(self, api_key, symbol):
        self.api_key = api_key
        self.symbol = symbol
        self.price = None
        self.prices = []

    def on_message(self, ws, message):
        data = json.loads(message)

        try:
            price = data["data"]["lastPrice"]
            self.price = price
            self.prices.append(price)
        except:
            pass

    def on_open(self, ws):
        ws.send(json.dumps({
            "action": "subscribe",
            "type": "trade",
            "symbol": self.symbol
        }))

    def start(self):

        url = "wss://api.fugle.tw/marketdata/v1.0/streaming"

        ws = websocket.WebSocketApp(
            url,
            header=[f"X-API-KEY: {self.api_key}"],
            on_message=self.on_message,
            on_open=self.on_open
        )

        thread = threading.Thread(target=ws.run_forever)
        thread.daemon = True
        thread.start()
