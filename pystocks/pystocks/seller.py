import logging


class seller(object):
    def __init__(self)-> list:
        self.logger = logging.getLogger("pystocks")

    def sell_stocks(self, money:int, stock_list:list, owned_stocks:list, max_trade_per_week:int)-> list:
        stocks_to_sell = list()
        return stocks_to_sell