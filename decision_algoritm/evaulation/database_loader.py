import sqlite3
from pathlib import Path


EVALUATION_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EVALUATION_DIR.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "trades.db"


def get_connection(db_path=None):
    database_path = Path(db_path) if db_path else DEFAULT_DB_PATH
    return sqlite3.connect(database_path)


def fetch_rows(query, params=None, db_path=None):
    with get_connection(db_path) as connection:
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()
        cursor.execute(query, params or [])
        return [dict(row) for row in cursor.fetchall()]


def load_decisions(db_path=None):
    return fetch_rows(
        """
        SELECT
            time,
            signal,
            price,
            sma,
            fear,
            action_strength,
            position_size,
            reason
        FROM decisions
        ORDER BY time
        """,
        db_path=db_path,
    )


def load_trades(db_path=None):
    return fetch_rows(
        """
        SELECT
            time,
            side,
            symbol,
            quantity,
            price,
            status,
            notional,
            details
        FROM trades
        ORDER BY time
        """,
        db_path=db_path,
    )
