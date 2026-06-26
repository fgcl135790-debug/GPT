def on_message(self, ws, message):
    data = json.loads(message)

    try:
        # 🔥 先印出來 debug（超重要）
        print(data)

        # 👉 Fugle 常見是直接 flat
        price = data.get("lastPrice")

        if price is None:
            return

        self.price = price
        self.prices.append(price)

        vol = data.get("volume", 1)
        self.volumes.append(vol)

    except Exception as e:
        print("WS error:", e)
print(message)
