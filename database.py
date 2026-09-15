import sqlite3

DATABASE_NAME = "wallet.db"


def create_connection():

    conn = sqlite3.connect(DATABASE_NAME)

    return conn


def create_tables():

    conn = create_connection()

    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        fullname TEXT NOT NULL,

        email TEXT NOT NULL UNIQUE,

        country TEXT NOT NULL,

        phone TEXT NOT NULL UNIQUE,

        password TEXT NOT NULL,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

    );
    """)

    conn.commit()

    conn.close()


if __name__ == "__main__":

    create_tables()

    print("Database Created Successfully.")