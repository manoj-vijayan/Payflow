import sqlite3

conn = sqlite3.connect("wallet.db")
cursor = conn.cursor()

try:

    cursor.execute("""
        ALTER TABLE users
        ADD COLUMN profile_image TEXT
    """)

    conn.commit()

    print("✅ profile_image column added successfully!")

except sqlite3.OperationalError as e:

    print("⚠", e)

conn.close()