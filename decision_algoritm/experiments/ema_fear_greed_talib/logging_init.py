import datetime
import logging
from logging.handlers import TimedRotatingFileHandler
from config_loader import BASE_DIR, config

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(message)s"

def setup_logging(symbol: str = ""):
    logging_config = config["logging"]
    logs_dir = BASE_DIR / logging_config.get("log_dir", "logs")
    logs_dir.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, logging_config.get("level", "INFO").upper(), logging.INFO))
    root_logger.handlers.clear()

    formatter = logging.Formatter(LOG_FORMAT)

    base_log = logging_config.get("combined_log_file", "ema_fng.log")
    if symbol:
        stem, _, ext = base_log.rpartition(".")
        combined_log_name = f"{stem}_{symbol.lower()}.{ext}" if stem else f"{symbol.lower()}_{base_log}"
    else:
        combined_log_name = base_log

    combined_handler = TimedRotatingFileHandler(
        logs_dir / combined_log_name,
        when="midnight",
        interval=1,
        backupCount=logging_config.get("backup_count", 14),
        encoding="utf-8",
    )
    combined_handler.setFormatter(formatter)

    session_log_name = logging_config.get("session_log_template", "run-{timestamp}.log").format(
        timestamp=datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    )
    if symbol:
        session_log_name = f"{symbol.lower()}_{session_log_name}"
    session_handler = logging.FileHandler(logs_dir / session_log_name, encoding="utf-8")
    session_handler.setFormatter(formatter)

    root_logger.addHandler(combined_handler)
    root_logger.addHandler(session_handler)
