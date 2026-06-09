import psycopg2

conn = psycopg2.connect(
    host="localhost",
    database="email_cleaner",
    user="admin",
    password= "supersecretpassword123"

)

cur = conn.cursor()

cur.execute("""
    CREATE TABLE IF NOT EXISTS User_Emails (
        email VARCHAR(255) PRIMARY KEY,
        refresh_token TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
""")

conn.commit()

cur.close()
conn.close()
