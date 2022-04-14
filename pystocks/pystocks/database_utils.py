import logging
import time

import urllib
import psycopg2
import yfinance as yf
import pandas as pd
import numpy as np
from sqlalchemy import create_engine


def create_tables(db_connection: "psycopg2.connection") -> str:
    logger = logging.getLogger("pystocks")

    commands = (
        """
        DROP TABLE IF EXISTS trend CASCADE;
        DROP TABLE IF EXISTS stocks;
        """,
        """
        CREATE TABLE stocks (
            ticker VARCHAR (6) PRIMARY KEY,
            name VARCHAR(255) UNIQUE NOT NULL,
            stock_id INT UNIQUE NOT NULL,
            index_name VARCHAR (10),
            pe NUMERIC(5,2) NOT NULL,
            peg NUMERIC(5,2) NOT NULL,
            eps NUMERIC(5,2) NOT NULL,
            pbook NUMERIC(5,2) NOT NULL,
            revenue NUMERIC(5,2) NOT NULL,
            ebitda NUMERIC(5,2) NOT NULL,
            dividend NUMERIC(5,2) NOT NULL
        );
        """,
        """
        CREATE TABLE trend (
            stock_id INT PRIMARY KEY,
            time TIMESTAMP NOT NULL,
            open NUMERIC(5, 2) NOT NULL,
            close NUMERIC(5,2) NOT NULL,
            high NUMERIC(5,2) NOT NULL,
            low NUMERIC(5,2) NOT NULL,
            return NUMERIC(5,2) ,
            cum_return NUMERIC(3,2),
            CONSTRAINT fk_stock_id 
                FOREIGN KEY(stock_id)
                REFERENCES stocks(stock_id)
        );
        """,
    )
    status = 0
    try:
        cur = db_connection.cursor()
        # create table one by one
        for command in commands:
            cur.execute(command)
        # close communication with the PostgreSQL database server
        cur.close()
        # commit the changes
        db_connection.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f"Error generating database: {error}")
        status = error

    logger.info(f"Database exiting with code {status}")

    return status


def write_to_database(
    db_con: "psycopg2.connection", table_name: str, dataframe: pd.DataFrame, mode: str
) -> None:
    status = db_con.info

    # db_info = {
    #     "user": status.user,
    #     "pass": status.password,
    #     "ip": status.host,
    #     "port": status.port,
    #     "db": status.dbname,
    #     "table": table_name,
    # }
    eng_template = "postgresql+psycopg2://{}:{}@{}:{}/{}"

    engine = create_engine(
        eng_template.format(
            status.name,
            status.password,
            status.host,
            status.port,
            status.dbname,
        )
    )

    dataframe.head(0).to_sql(
        table_name, engine, if_exists=mode, index=False
    )  # drops old table and creates new empty table

    conn = engine.raw_connection()
    cur = conn.cursor()
    output = io.StringIO()
    dataframe.to_csv(output, sep="\t", header=False, index=False)
    output.seek(0)
    contents = output.getvalue()
    cur.copy_from(output, table_name, null="")  # null values become ''
    conn.commit()


def build_stock_dataframe(read_rows=None) -> pd.DataFrame:
    logger = logging.getLogger("pystocks")

    max_tick = 6
    max_text = 255

    nasdaq_url = "https://datahub.io/core/nasdaq-listings/r/nasdaq-listed.csv"
    nyse_url = "https://datahub.io/core/nyse-other-listings/r/nyse-listed.csv"
    nasdaq_data = pd.read_csv(nasdaq_url, nrows=read_rows)
    nyse_data = pd.read_csv(nyse_url, nrows=read_rows)

    ticker_data = pd.concat((nasdaq_data["Symbol"], nyse_data["ACT Symbol"]))
    names = pd.concat((nasdaq_data["Company Name"], nyse_data["Company Name"]))

    num_tickers = ticker_data.size

    db = {
        "ticker": ticker_data,
        "name": names,
        "stock_id": np.arange(0, num_tickers, dtype=np.int32),
        "index_name": pd.array(num_tickers * [None], dtype="string"),
        "pe": np.zeros(num_tickers, dtype=np.float32),
        "peg": np.zeros(num_tickers, dtype=np.float32),
        "eps": np.zeros(num_tickers, dtype=np.float32),
        "pbook": np.zeros(num_tickers, dtype=np.float32),
        "revenue": np.zeros(num_tickers, dtype=np.float32),
        "ebitda": np.zeros(num_tickers, dtype=np.float32),
        "dividend": np.zeros(num_tickers, dtype=np.float32),
    }

    logger.info("Generating dataframe...")
    stock_db = pd.DataFrame(db)

    get_index_components(stock_db, logger)

    gen_static_info(stock_db, logger)

    logger.info("Finished generating stock database")

    pd.set_option("display.max_rows", None, "display.max_columns", None)

    return stock_db


def get_index_components(stock_df: pd.DataFrame, log: logging.Logger):
    indices = pd.read_html("https://finance.yahoo.com/world-indices/")[0]

    missing_components = 0
    for index in indices["Symbol"]:
        index = index.strip()
        component_url = f"https://finance.yahoo.com/quote/%5E{index[1:]}/components?p=%5E{index[1:]}"

        try:
            components = pd.read_html(component_url)[0]

            info = stock_df["ticker"].isin(components["Symbol"])

            stock_df.loc[info == True, "index_name"] = index

        except ImportError as error:
            missing_components += 1
            continue
        except urllib.error.HTTPError:
            log.info(f"Couldn't reach yf.")

    if missing_components:
        log.warning(
            f"Couldn't find data for {missing_components} components of {indices.size}"
        )

    log.info("Finished identifying index components")


def gen_static_info(stock_df: pd.DataFrame, log: logging.Logger):
    component_err = 0

    for name in stock_df["ticker"]:
        ticker = yf.Ticker(name)
        try:
            row = stock_df.loc[stock_df["ticker"] == name].index

            stock_df.loc[row, "pe"] = ticker.info["forwardPE"]
            stock_df.loc[row, "peg"] = ticker.info["pegRatio"]
            stock_df.loc[row, "eps"] = ticker.info["forwardEps"]
            stock_df.loc[row, "pbook"] = ticker.info["priceToBook"]
            stock_df.loc[row, "revenue"] = ticker.info["enterpriseToRevenue"]
            stock_df.loc[row, "ebitda"] = ticker.info["enterpriseToEbitda"]
            stock_df.loc[row, "dividend"] = ticker.info["dividendYield"]
        except IndexError as error:
            component_err += 1
        except KeyError as error:
            component_err += 1

    if component_err:
        log.warning(f"Encountered {component_err} errors downloading static data")


def build_history_dataframe(
    stock_name: str,
    stock_id: int,
    history: str,
) -> pd.DataFrame:
    stock = yf.Ticker(stock_name)

    try:
        stock_hist = stock.history(period=history, interval="5d")

        not_wanted = ["Volume", "Dividends", "Stock Splits"]
        to_remove = set(not_wanted).intersection(stock_hist.keys())

        stock_hist = stock_hist.drop(labels=to_remove, axis=1)
        stock_hist = stock_hist.rename(
            columns={
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
            },
        )
        stock_hist["stock_id"] = stock_id
        stock_hist["time"] = stock_hist.index
    except KeyError as error:
        print(error)

    return stock_hist


if __name__ == "__main__":
    addr = "localhost"
    con = psycopg2.connect(
        host=addr, database="stocks", user="postgres", password="nhy6nji9NHY^NJI("
    )

    # Initialize tables
    create_tables(con)
    exit(0)
    # Generate 10 rows of original dataframe
    stocks = build_stock_dataframe(10)

    # Optional: read/write dataframe to pickle
    # print("To pickle Rick")
    # stocks.to_pickle("stocks.pdy")

    # print("I'm pickle Rick!")
    # stocks = pd.read_pickle("stocks.pdy")

    # db_info = {
    #     "user": "postgres",
    #     "pass": "postgres",
    #     "ip": "172.16.238.39",
    #     "port": "5432",
    #     "db": "pydb",
    #     "table": "trend",
    # }

    # Fill trend with historical data
    for index, row in stocks.iterrows():
        stock_hist = build_history_dataframe(row["ticker"], row["stock_id"], "1mo")
        write_to_database(con, "trend", stock_hist, "append")

    # Set to write to stocks instead of trend
    # db_info["table"] = "stocks"

    # Write stocks table
    # This is done last because stocks depends on trend
    write_to_database(con, "stocks", stocks, "replace")
