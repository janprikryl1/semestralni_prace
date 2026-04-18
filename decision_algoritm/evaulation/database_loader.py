import sqlite3

conn = sqlite3.connect("../trades.db")
cursor = conn.cursor()

cursor.execute("SELECT * FROM trades")
rows = cursor.fetchall()

for row in rows:
    print(row)

#statistics
buy_count = sum(1 for r in rows if r[1] == "BUY")
sell_count = sum(1 for r in rows if r[1] == "SELL")

print("BUY:", buy_count)
print("SELL:", sell_count)

#money spent
total_spent = sum(r[3] * r[4] for r in rows if r[1] == "BUY")
print("Celkem utraceno:", total_spent)

import matplotlib.pyplot as plt

times = [r[0] for r in rows]
prices = [r[4] for r in rows]

plt.plot(times, prices)
plt.xticks(rotation=45)
plt.title("Vývoj obchodů")
plt.show()

conn.close()