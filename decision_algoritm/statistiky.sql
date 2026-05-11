-- Most purchases by strategy
SELECT symbol, COUNT(*) AS cnt
FROM trades
WHERE side = 'BUY' AND trading_type = 'SMA_FG'  -- nebo 'EMA_FG'
GROUP BY symbol
ORDER BY cnt DESC
LIMIT 5;

-- Most sales by strategy
SELECT symbol, COUNT(*) AS cnt
FROM trades
WHERE side = 'SELL' AND trading_type = 'SMA_FG'
GROUP BY symbol
ORDER BY cnt DESC
LIMIT 5;

-- The most common purchase price by strategy
SELECT ROUND(price, 2) AS price, COUNT(*) AS cnt
FROM trades
WHERE side = 'BUY' AND trading_type = 'SMA_FG'
GROUP BY price
ORDER BY cnt DESC
LIMIT 5;

-- Most common selling price by strategy
SELECT ROUND(price, 2) AS price, COUNT(*) AS cnt
FROM trades
WHERE side = 'SELL' AND trading_type = 'SMA_FG'
GROUP BY price
ORDER BY cnt DESC
LIMIT 5;

-- The most common fees by strategy
SELECT ROUND(ABS(notional - quantity * price), 4) AS fee, COUNT(*) AS cnt
FROM trades
WHERE notional IS NOT NULL AND trading_type = 'SMA_FG'
GROUP BY fee
ORDER BY cnt DESC
LIMIT 5;

-- The most common time to shop, by strategy
SELECT HOUR(time) AS hour, COUNT(*) AS cnt
FROM trades
WHERE side = 'BUY' AND trading_type = 'SMA_FG'
GROUP BY hour
ORDER BY cnt DESC
LIMIT 5;

-- Average transaction value
SELECT trading_type, side,
       ROUND(AVG(notional), 4)  AS avg_notional,
       ROUND(SUM(notional), 4)  AS total_notional
FROM trades
WHERE notional IS NOT NULL
GROUP BY trading_type, side
ORDER BY trading_type, side;

-- Ratio BUY vs. SELL
SELECT symbol,
       SUM(side = 'BUY')  AS buys,
       SUM(side = 'SELL') AS sells,
       ROUND(SUM(side = 'BUY') / NULLIF(SUM(side = 'SELL'), 0), 2) AS buy_sell_ratio
FROM trades
GROUP BY symbol
ORDER BY symbol;

-- Most common day in week – BUY
SELECT DAYOFWEEK(time) AS dow,
       DAYNAME(time)   AS day_name,
       COUNT(*)        AS cnt
FROM trades
WHERE side = 'BUY'
GROUP BY dow, day_name
ORDER BY cnt DESC;

-- Most common day in week - SELL
SELECT DAYOFWEEK(time) AS dow,
       DAYNAME(time)   AS day_name,
       COUNT(*)        AS cnt
FROM trades
WHERE side = 'SELL'
GROUP BY dow, day_name
ORDER BY cnt DESC;

-- Fear & Greed at signal levels
SELECT trading_type, `signal`,
       ROUND(AVG(fear), 1) AS avg_fear,
       MIN(fear)           AS min_fear,
       MAX(fear)           AS max_fear
FROM decisions
WHERE fear IS NOT NULL
GROUP BY trading_type, `signal`
ORDER BY trading_type, `signal`;

-- Fear vs. action_strength (SMA_FG)
SELECT
    CASE
        WHEN fear BETWEEN  0 AND 24 THEN '0-24 Extreme Fear'
        WHEN fear BETWEEN 25 AND 44 THEN '25-44 Fear'
        WHEN fear BETWEEN 45 AND 55 THEN '45-55 Neutral'
        WHEN fear BETWEEN 56 AND 75 THEN '56-75 Greed'
        ELSE                              '76-100 Extreme Greed'
    END AS fear_zone,
    ROUND(AVG(action_strength), 4) AS avg_strength,
    COUNT(*) AS cnt
FROM decisions
WHERE trading_type = 'SMA_FG'
  AND fear IS NOT NULL
  AND action_strength IS NOT NULL
GROUP BY fear_zone
ORDER BY MIN(fear);
