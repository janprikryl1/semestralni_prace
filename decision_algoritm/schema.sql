-- MySQL schema for unified trading decisions and trades log

CREATE TABLE IF NOT EXISTS decisions (
    id            INT UNSIGNED     NOT NULL AUTO_INCREMENT,
    time          DATETIME(6)      NOT NULL,
    trading_type  ENUM('SMA_FG', 'EMA_FG') NOT NULL,
    `signal`      VARCHAR(10)      NOT NULL,
    symbol        VARCHAR(20)      NOT NULL,
    price         DECIMAL(18, 8)   NOT NULL,
    sma           DECIMAL(18, 8)   NULL,     -- SMA_FG only
    ema           DECIMAL(18, 8)   NULL,     -- EMA_FG only
    fear          TINYINT UNSIGNED NULL,
    action_strength DECIMAL(8, 6)  NULL,     -- SMA_FG only
    position_size DECIMAL(8, 6)   NULL,
    reason        TEXT             NULL,
    PRIMARY KEY (id),
    INDEX idx_decisions_time (time),
    INDEX idx_decisions_type (trading_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS trades (
    id            INT UNSIGNED     NOT NULL AUTO_INCREMENT,
    time          DATETIME(6)      NOT NULL,
    trading_type  ENUM('SMA_FG', 'EMA_FG') NOT NULL,
    side          ENUM('BUY', 'SELL')       NOT NULL,
    symbol        VARCHAR(20)      NOT NULL,
    quantity      DECIMAL(18, 8)   NOT NULL,
    price         DECIMAL(18, 8)   NOT NULL,
    notional      DECIMAL(18, 8)   NULL,
    status        VARCHAR(20)      NOT NULL,
    details       TEXT             NULL,
    PRIMARY KEY (id),
    INDEX idx_trades_time (time),
    INDEX idx_trades_type (trading_type),
    INDEX idx_trades_symbol (symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
