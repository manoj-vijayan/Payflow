import sqlite3

conn = sqlite3.connect("wallet.db")
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(bank_accounts)")

columns = cursor.fetchall()

for column in columns:
    print(column)

conn.close()
