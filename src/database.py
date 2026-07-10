import psycopg2
import os
from dotenv import load_dotenv
load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

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
                refresh_token TEXT ,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        print("Database setup complete.")
    except Exception as e:
        print(f"Error setting up database: {e}")
        raise

def save_user_to_db(email, token_filename):
    conn, cur = connect_db()
    if conn is None:
        return False
    try:
        cur.execute(
            "INSERT INTO User_Emails (email, refresh_token) VALUES (%s, %s) ON CONFLICT (email) DO UPDATE SET refresh_token = EXCLUDED.refresh_token",
            (email, token_filename)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"Failed to save user: {e}")
        raise

def get_token_filename(email):
    try:
        connect_db()
        cur.execute("SELECT refresh_token FROM User_Emails WHERE email = %s", (email,))
        row = cur.fetchone()
        if row and row[0]:
            return row[0]
        return None
    except Exception as e:
        print(f"Failed to get token: {e}")
        raise

if __name__ == "__main__":
    init_db()
