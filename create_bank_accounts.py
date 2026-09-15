import sqlite3

conn = sqlite3.connect("wallet.db")
cursor = conn.cursor()

cursor.execute("""

CREATE TABLE IF NOT EXISTS bank_accounts (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    user_id INTEGER NOT NULL,

    bank_name TEXT NOT NULL,

    account_number TEXT NOT NULL UNIQUE,

    ifsc TEXT NOT NULL,

    balance REAL DEFAULT 0,

    FOREIGN KEY(user_id) REFERENCES users(id)

)

""")

conn.commit()

print("✅ bank_accounts table created successfully!")

conn.close()