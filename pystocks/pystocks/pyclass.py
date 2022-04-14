"""
Pystocks superclass to serve as framework for stock trading. Can be run as
main to test a single instance.
"""
import logging
import time
import sys

import psycopg2
import yfinance as yf

import pystocks as ps


class pystocks(object):
    """Trading superclass for Python stockbot. Runs as a daemon with the
        run() function

    Args:
        pool: Money resources available for the bot.
        log_file (optional): File to log to. Also logs to stdout by default.
    """

    def __init__(
        self,
        pool: int,
        log_file: str = "pystocks.log",
        postgres_params={"host": "localhost"},
    ) -> None:
        self.investment = pool
        self.pool = pool

        self.interval = 10  # 5*60

        self.db_con = psycopg2.connect(**postgres_params)
        self.init_logger(log_file)

        self.buyer = ps.buyer()
        self.seller = ps.seller()
        self.database = ps.database(self.db_con)

        self.stock_ticks = None
        self.owned_stocks = None

    def __del__(self):
        try:
            self.db_con.close()
        except AttributeError:
            self.logger.error("Tried to close non-existant connection")

    def run(self) -> None:
        """
        Main class process, runs while the process is alive. Calls the stocks
        to buy, performs buying/selling actions, and updates the stock database.
        """
        while True:
            time.sleep(self.interval)
            print("Hello world")

            self.stock_ticks = self.database.update()

            stocks_to_buy = self.buyer.buy_stocks(
                self.pool, self.stock_ticks, self.owned_stocks
            )
            stocks_to_sell = self.seller.sell_stocks(
                self.pool, self.stock_ticks, self.owned_stocks
            )

            stock_misses = self.stock_actions(stocks_to_buy, stocks_to_sell)

    def init_logger(self, log_file: str) -> None:
        """Initialize logger to print to log file and stdout.

        Args:
            log_file: The file to write logs to. Overwrites existing log files.
        """
        logHandler = logging.FileHandler(log_file, encoding="utf-8", mode="w")
        printHandler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(module)s - %(levelname)s - %(message)s"
        )
        logHandler.setFormatter(formatter)
        printHandler.setFormatter(formatter)
        self.logger = logging.getLogger("pystocks")
        self.logger.addHandler(logHandler)
        self.logger.addHandler(printHandler)
        self.logger.setLevel(logging.DEBUG)

    def stock_actions(self, buy_list: list, sell_list: list) -> list:
        """Perform trading actions on stocks chosen to be bought and sold.
        Currently uses paper trading and closing stock prices.

        Args:
            buy_list: List of stocks to buy, chosen by the buyer class.
            sell_list: List of stocks to sell, chosen by the seller class.

        Returns:
            List of stocks that failed to be bought due to pool size.
        """
        # Temporary stock buyer/seller
        total_earned = 0
        for stock in sell_list:
            tick = yf.Ticker(stock)
            # Arbitrary sell price from last day closing price.
            # Real prices will come from actual buy/sell
            price = tick.history(
                "1h",
            ).Close[0]
            try:
                # "Sell" stock
                self.owned_stocks.remove(stock)
                self.pool += price
                total_earned += price
            except ValueError:
                self.logger.warning(f"Tried to sell unowned stock {stock}")

        total_spent = 0
        # Some stocks may not get bought. Track them
        unbought_stocks = buy_list.copy()
        for stock in buy_list:
            tick = yf.Ticker(stock)
            price = tick.history(
                "1h",
            ).Close[0]
            print("Buy price is", price)
            if price <= self.pool:
                self.pool -= price
                total_spent += price
                self.owned_stocks.append(stock)
                unbought_stocks.remove(stock)
            else:
                self.logger.info(f"Pool {self.pool} too small for {stock} at {price}")
                buy_list.remove(stock)

        if sell_list:
            self.logger.info(f"Sold {sell_list} for {total_earned}")
        if buy_list:
            self.logger.info(f"Bought {buy_list} for {total_spent}")
        if unbought_stocks:
            self.logger.info(
                f"Pool {self.pool} too small to buy stocks {unbought_stocks}"
            )

        # Return unbought_stocks for reference
        return unbought_stocks

    def print_stocks(self) -> None:
        """ Print owned stocks to terminal."""
        print(f"Current stocks:\n\t{self.owned_stocks}")

    def print_profit(self) -> None:
        """Print class worth to terminal.
        TODO: Total net worth and print it.
        """
        print(f"Started at {self.investment}, current is {self.pool}")


if __name__ == "__main__":
    money = 1000

    post_params = {
        "host": "172.16.238.39",
        "database": "pydb",
        "user": "postgres",
        "password": "postgres",
    }

    stocks = pystocks(money, postgres_params=post_params)

    stocks.run()
