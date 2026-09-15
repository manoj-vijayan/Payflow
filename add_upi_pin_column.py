import sqlite3

conn = sqlite3.connect("wallet.db")
cursor = conn.cursor()

try:

    cursor.execute("""
        ALTER TABLE users
        ADD COLUMN upi_pin TEXT
    """)

    conn.commit()

    print("✅ upi_pin column added successfully!")

except sqlite3.OperationalError as e:

    print("⚠", e)

conn.close()