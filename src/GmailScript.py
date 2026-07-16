import os
import pickle
import pandas as pd
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

import database


SCOPES = ['https://www.googleapis.com/auth/gmail.modify']




def login(service):
    
    return service.users().getProfile(userId='me').execute()
    

def get_gmail_service(User_Emails = None):
    creds = None
    token_filename = f"{User_Emails}_token.pickle" if User_Emails else "temp_token.pickle"
    
    if User_Emails:
        saved_token_filename = database.get_token_filename(User_Emails)
        if saved_token_filename:
            token_filename = saved_token_filename
    if os.path.exists(token_filename):
        with open(token_filename, 'rb') as token:
            creds = pickle.load(token)
    else:
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
        
        with open(token_filename, 'wb') as token:
            pickle.dump(creds, token)

    return build('gmail', 'v1', credentials=creds) , token_filename

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

def trash_emails_from_sender(service, sender_email):
    trashed = 0
    page_token = None
    while True:
        results = service.users().messages().list(
            userId='me',
            q=f'from:{sender_email} category:promotions',
            maxResults=100,
            pageToken=page_token
        ).execute()
        messages = results.get('messages', [])
        if not messages:
            break
        for msg in messages:
            trash_email(service, msg['id'])
            trashed += 1
        page_token = results.get('nextPageToken')
        if not page_token:
            break
    return trashed

def filter_by_date(service, start_date, end_date):
    start_date = start_date.replace("-", "/")
    end_date = end_date.replace("-", "/")
    # Gmail API uses the format YYYY/MM/DD for date filtering, so we replace "-" with "/"
    # The query will filter emails that are after the start_date and before the end_date, and also in the promotions category.
    query = f'after:{start_date} before:{end_date} category:promotions'

    messages = []
    page_token = None
    ''' Loop through pages of results with the pageToken parameter until 
    
    there are no more pages left. This allows us to retrieve all messages that match the query.
    '''
    while True:            
        results = service.users().messages().list(userId='me', q=query, pageToken=page_token).execute()
        messages.extend(results.get('messages', []))
        page_token = results.get('nextPageToken')
        if not page_token:
            break

    return messages


def build_service(creds):
    return build('gmail', 'v1', credentials=creds)

def save_creds(creds, token_filename):
    with open(token_filename, 'wb') as token:
        pickle.dump(creds, token)

def load_creds(email):
    token_filename = database.get_token_filename(email) or f"{email}_token.pickle"
    if os.path.exists(token_filename):
        with open(token_filename, 'rb') as token:
            return pickle.load(token)
    return None



    
        
       
        
    
