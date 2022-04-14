import logging


class buyer(object):
    def __init__(self)-> None:
        self.logger = logging.getLogger("pystocks")

    def buy_stocks(self, money: int, stock_list: dict, owned_stocks: list )-> list:
        stocks_to_buy = dict() #{"TSLA": 1.3} 
        



        # self.logger.info("Bought a stock")
        return stocks_to_buy