import datetime
import logging
from logging.handlers import TimedRotatingFileHandler
from config_loader import BASE_DIR, config

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(message)s"

def setup_logging():
    logging_config = config["logging"]
    logs_dir = BASE_DIR / logging_config.get("log_dir", "logs")
    logs_dir.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, logging_config.get("level", "INFO").upper(), logging.INFO))
    root_logger.handlers.clear()

    formatter = logging.Formatter(LOG_FORMAT)

    combined_handler = TimedRotatingFileHandler(
        logs_dir / logging_config.get("combined_log_file", "ema_fng.log"),
        when="midnight",
        interval=1,
        backupCount=logging_config.get("backup_count", 14),
        encoding="utf-8",
    )
    combined_handler.setFormatter(formatter)

    session_log_name = logging_config.get("session_log_template", "run-{timestamp}.log").format(
        timestamp=datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    )
    session_handler = logging.FileHandler(logs_dir / session_log_name, encoding="utf-8")
    session_handler.setFormatter(formatter)

    root_logger.addHandler(combined_handler)
    root_logger.addHandler(session_handler)
