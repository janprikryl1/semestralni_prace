import datetime
import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

TRADING_TYPE = "SMA_FG"


def _connect():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", 3306)),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE"),
    )


def initialize_db():
    pass


def save_decision(signal, symbol, price, sma, fear, action_strength, position_size, reason):
    with _connect() as conn:
        conn.cursor().execute(
            """
            INSERT INTO decisions
                (time, trading_type, `signal`, symbol, price, sma, fear, action_strength, position_size, reason)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                datetime.datetime.now(),
                TRADING_TYPE,
                signal,
                symbol,
                price,
                sma,
                fear,
                action_strength,
                position_size,
                reason,
            ),
        )
        conn.commit()


def save_trade(side, symbol, quantity, price, notional, status, details):
    with _connect() as conn:
        conn.cursor().execute(
            """
            INSERT INTO trades
                (time, trading_type, side, symbol, quantity, price, notional, status, details)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                datetime.datetime.now(),
                TRADING_TYPE,
                side,
                symbol,
                quantity,
                price,
                notional,
                status,
                details,
            ),
        )
        conn.commit()
