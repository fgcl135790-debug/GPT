import yfinance as yf

class MarketData:
    def get_price(self, symbol):
        data = yf.download(symbol, period="1d", interval="1m")
        return data
