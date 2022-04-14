import logging
import yfinance as yf
import pandas as pd
#poopoo
class database(object):
    tickers = {}
    def __init__(self):
        self = self

    def history(self, name):
        stock = yf.Ticker(name)
        hist = stock.history('1y')
        return hist


    @staticmethod
    def getter(self):
        url = 'https://finance.yahoo.com/gainers'

        dfs = pd.read_html(url)

        for i in range(len(dfs[0]['Symbol'])):
            hist = database.history(dsf[i]['Symbol'])
            self.tickers = tickers.update({dfs[i]['Symbol']: hist})
        return self.tickers

    
    def update(self):
        for key in tickers:
            tickers[key] = database.history(key)
        return tickers



    def flush(self):
        return 0
db = database().getter()
print(db)
