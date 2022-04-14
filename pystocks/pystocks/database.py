import logging

import psycopg2
import yfinance as yf
import pandas as pd
from collections import Counter
import pystocks

# TODO: Construct database queries to keep track of data


class stock(object):
    def __init__(self, attr=None):
        self.name = None
        self.ticker = None
        self.stock_id = None
        self.buy_time = None

        if attr is not None:
            self.components_from_dict(**attr)

    def components_from_dict(attributes: dict):
        self.name = attributes["name"]
        self.ticker = yf.Ticker(self.name)
        self.stock_id = attributes["stock_id"]
        self.buy_time = attributes["buy_time"]


class database(object):
    def __init__(self, postgres_connection: "psycopg2.connection") -> None:
        self.post_con = postgres_connection
        self.dataframe = None
        self.logger = logging.getLogger("pystocks")

        self.tickers = list()

        self.initialize_db()

    def query_from_desire(self, tolerance, desire**): # justice
        # tolerance in percent ie 10% = .10
        # pass a dictionary of desired values ie {PEG : 10, PE : 2} and finds tickers
        # that hold those values
        ping_good = {}
        good_stock = []
        for key in desire:
            query = "SELECT ticker, {0} from stocks".format(key)
            curse = self.post_con.cursor()
            curse.execute(query)
            data = curse.fetchall()
            upper = desire[key] + desire[key] * (tolerance/100)
            lower = desire[key] - desire[key] * (tolerance/100)
            for row in range(len(data)):
                if type(data[row][1]) == NULL:
                    break
                else if data[row][1] <= upper and >= lower: 
                    good_stock = good_stock.append(row[0])
                else:
                    del data[row]
        counts = Counter(good_stock)  # returns a dictionary with the amount a stock met criteria
        counts = sorted(counts.values())
        return counts

        #query = "select ticker, pe, peg, eps, pbook, revenue, ebitd, dividend from stocks" 
        #curse = self.post_con.cursor()      all might be dumb but idk
        #curse,execute(query)
        #data = curse.fetchall() # returns a list of data wi
        #for row in data:
        #    if 


        



    def initialize_db(self):
        # Check if tables exist. If they do, return
        cur = self.post_con.cursor()
        commands = (
            """SELECT to_regclass('stocks');""",
            """SELECT to_regclass('trend');""",
        )
        tables = list()
        for command in commands:
            cur.execute(command)
            tables.append(cur.fetchall()[0][0])

        cur = None
        self.logger.info(
            f"Found tables {tables} in database {self.post_con.info.dbname}"
        )
        if tables == ["stocks", "trend"]:
            self.logger.info("Database already initialized, continuing.")
            return 0

        db_status = pystocks.create_tables(self.post_con)
        stocks_df = pystocks.build_stock_dataframe(10)

        # Fill trend with historical data
        for index, row in stocks_df.iterrows():
            stock_hist = build_history_dataframe(row["ticker"], row["stock_id"], "1mo")
            write_to_database(self.post_con, "trend", stock_hist, "append")

        # Write stocks table
        # This is done last because stocks depends on trend
        write_to_database(self.post_con, "stocks", stocks_df, "replace")

        return db_status

    def get_from_db(self) -> pd.DataFrame:
        # TODO: return data needed from database
        return 0  # self.tickers

    def update(self) -> None:
        # TODO: create update rules to write to
        # # Fill trend with historical data
        # for index, row in stocks_df.iterrows():
        #     stock_hist = build_history_dataframe(row["ticker"], row["stock_id"], "1mo")
        #     write_to_database(self.post_con, "trend", stock_hist, "append")
        return 0

    # Do we need this still?
    # def flush(self):
    # return 0


if __name__ == "__main__":
    addr = "172.16.238.39"
    con = psycopg2.connect(
        host=addr, database="pydb", user="postgres", password="postgres"
    )

    db = database(con)