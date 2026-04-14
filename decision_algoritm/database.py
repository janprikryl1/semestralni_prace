import sqlite3
import datetime
from config_loader import config

def initialize_db():
    conn = sqlite3.connect(config['database']['db_file'])
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS decisions (
        time TEXT,
        signal TEXT,
        price REAL,
        sma REAL,
        fear INTEGER
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trades (
        time TEXT,
        side TEXT,
        symbol TEXT,
        quantity REAL,
        price REAL,
        status TEXT
    )
    """)

    conn.commit()
    conn.close()

def save_decision(signal, price, sma, fear):
    conn = sqlite3.connect(config['database']['db_file'])
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO decisions VALUES (?, ?, ?, ?, ?)
    """, (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), signal, price, sma, fear))

    conn.commit()
    conn.close()

def save_trade(side, symbol, quantity, price, status):
    conn = sqlite3.connect(config['database']['db_file'])
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO trades VALUES (?, ?, ?, ?, ?, ?)
    """, (
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        side,
        symbol,
        quantity,
        price,
        status
    ))

    conn.commit()
    conn.close()

# Initialize database when this module is imported
initialize_db()
