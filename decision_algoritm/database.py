import sqlite3
import datetime
from config_loader import config


def ensure_column(cursor, table_name, column_name, column_definition):
    cursor.execute(f"PRAGMA table_info({table_name})")
    existing_columns = {column[1] for column in cursor.fetchall()}
    if column_name not in existing_columns:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")


def initialize_db():
    conn = sqlite3.connect(config['database']['db_file'])
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS decisions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        time TEXT,
        signal TEXT,
        price REAL,
        sma REAL,
        fear INTEGER,
        action_strength REAL,
        position_size REAL,
        reason TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        time TEXT,
        side TEXT,
        symbol TEXT,
        quantity REAL,
        price REAL,
        notional REAL,
        status TEXT,
        details TEXT
    )
    """)

    ensure_column(cursor, "decisions", "action_strength", "REAL")
    ensure_column(cursor, "decisions", "position_size", "REAL")
    ensure_column(cursor, "decisions", "reason", "TEXT")

    ensure_column(cursor, "trades", "notional", "REAL")
    ensure_column(cursor, "trades", "details", "TEXT")

    conn.commit()
    conn.close()


def save_decision(signal, price, sma, fear, action_strength, position_size, reason):
    conn = sqlite3.connect(config['database']['db_file'])
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO decisions (
        time,
        signal,
        price,
        sma,
        fear,
        action_strength,
        position_size,
        reason
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        signal,
        price,
        sma,
        fear,
        action_strength,
        position_size,
        reason
    ))

    conn.commit()
    conn.close()


def save_trade(side, symbol, quantity, price, notional, status, details):
    conn = sqlite3.connect(config['database']['db_file'])
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO trades (
        time,
        side,
        symbol,
        quantity,
        price,
        notional,
        status,
        details
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        side,
        symbol,
        quantity,
        price,
        notional,
        status,
        details
    ))

    conn.commit()
    conn.close()

# Initialize database when this module is imported
initialize_db()
