import sqlite3

conn = sqlite3.connect("wallet.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS payment_requests (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    sender_id INTEGER NOT NULL,

    receiver_id INTEGER NOT NULL,

    amount REAL NOT NULL,

    status TEXT DEFAULT 'PENDING',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(sender_id) REFERENCES users(id),

    FOREIGN KEY(receiver_id) REFERENCES users(id)

)
""")

conn.commit()
conn.close()

print("payment_requests table created successfully")