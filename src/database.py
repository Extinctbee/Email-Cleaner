import psycopg2
import os

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "email_cleaner")
DB_USER = os.getenv("DB_USER", "admin")
DB_PASSWORD = os.getenv("DB_PASSWORD", "supersecretpassword123")

conn = None
cur = None

def connect_db():
    global conn, cur
    if conn is None:
        print(f"Connecting to {DB_USER}@{DB_HOST}:{DB_NAME}")
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cur = conn.cursor()
    return conn, cur

def init_db():
    try:
        connect_db()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS User_Emails (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) unique NOT NULL,
                refresh_token TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        print("Database setup complete.")
    except Exception as e:
        print(f"Error setting up database: {e}")

if __name__ == "__main__":
    init_db()
