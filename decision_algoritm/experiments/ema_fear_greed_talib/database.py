import datetime
import sqlite3
from config_loader import BASE_DIR, config

DB_PATH = BASE_DIR / config["database"]["db_file"]

def initialize_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS decisions (
                time TEXT,
                signal TEXT,
                price REAL,
                ema REAL,
                fear INTEGER,
                position_size REAL,
                reason TEXT
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS trades (
                time TEXT,
                side TEXT,
                symbol TEXT,
                quantity REAL,
                price REAL,
                notional REAL,
                status TEXT,
                details TEXT
            )
            """
        )
        conn.commit()


def save_decision(signal, price, ema, fear, position_size, reason):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO decisions (time, signal, price, ema, fear, position_size, reason)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                signal,
                price,
                ema,
                fear,
                position_size,
                reason,
            ),
        )
        conn.commit()


def save_trade(side, symbol, quantity, price, notional, status, details):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO trades (time, side, symbol, quantity, price, notional, status, details)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
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


initialize_db()
