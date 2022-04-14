import logging

import buyer
import seller
import database

class pystocks(object):
    def __init__(self, pool):
        print("Hello world")
        self.pool = pool

        self.buyer = buyer.buyer()
        self.seller = seller.seller()
        self.database = database.database()

        self.run()
    
    def run(self):
        while True:
            self.buyer.buy_stocks(self.pool)
            self.seller.sell_stocks()

            self.database.update()

    def print_stocks(self):
        print("This will print the stocks!")
        return
    def log(self):
        print("This will log our stuff!")
        return
    def print_profit(self):
        print("No profit yet!")
        return
    def sell_stocks(self):
        print("oof")
        return
