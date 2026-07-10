import os
import pickle
import pandas as pd
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

import database


SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

# Database connection (lazy - only connect when needed)
db_conn = None
db_cur = None

def get_db_connection():
    global db_conn, db_cur
    if db_conn is None:
        try:
            db_conn = psycopg2.connect(
                host=os.getenv("DB_HOST", "localhost"),
                database=os.getenv("DB_NAME", "email_cleaner"),
                user=os.getenv("DB_USER", "admin"),
                password=os.getenv("DB_PASSWORD", "supersecretpassword123")
            )
            db_cur = db_conn.cursor()
            
            # Create table if it doesn't exist
            db_cur.execute("""
                CREATE TABLE IF NOT EXISTS User_Emails (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    refresh_token TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            db_conn.commit()
        except Exception as e:
            st.error(f"Database connection failed: {e}")
            return None, None
    return db_conn, db_cur

def save_user_to_db(email, token_filename):
    conn, cur = get_db_connection()
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
        st.error(f"Failed to save user: {e}")
        return False

def login(service, userId):
    User = service.users().getProfile(userId='me').execute()
    return User

def get_gmail_service(User_Emails):
    creds = None
    token_filename = f"{User_Emails}_token.pickle"
    
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    creds = flow.run_local_server(port=0)
    
    with open(token_filename, 'wb') as token:
        pickle.dump(creds, token)

    return build('gmail', 'v1', credentials=creds)

def scan_inbox_by_batches(service, max_pages=10):
    sender_counts = {}
    page_token = None
    pages_scanned = 0

    def callback(request_id, response, exception):
        if exception is not None:
            return
        headers = response.get('payload', {}).get('headers', [])
        for header in headers:
            if header['name'] == 'From':
                sender = header['value']
                sender_counts[sender] = sender_counts.get(sender, 0) + 1
    
    print("Starting inbox scan...")
    
    while pages_scanned < max_pages:
        results = service.users().messages().list(
            userId='me', 
            q='category:promotions',
            maxResults=100, 
            pageToken=page_token
        ).execute()
        
        messages = results.get('messages', [])
        if not messages:
            break

        batch = service.new_batch_http_request(callback=callback)
        for msg in messages:
            batch.add(service.users().messages().get(userId='me', id=msg['id'], format='metadata', metadataHeaders=['From']))
        
        batch.execute()
        
        page_token = results.get('nextPageToken')
        pages_scanned += 1
        print(f"Scanned page {pages_scanned}")
        
        if not page_token:
            break
            
    return sender_counts

def trash_email(service, message_id):
    try:
        service.users().messages().trash(userId='me', id=message_id).execute()
        print(f"Trashed: {message_id}")
    except Exception as e:
        print(f"Error: {e}")


def build_service(creds):
    return build('gmail', 'v1', credentials=creds)

def save_creds(creds, token_filename):
    with open(token_filename, 'wb') as token:
        pickle.dump(creds, token)



    
        
       
        
    
