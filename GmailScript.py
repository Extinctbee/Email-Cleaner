import os
import pickle
import pandas as pd
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import streamlit as st
import database.py
# 1. Define what your app is allowed to do (Read and Delete access)
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']



def get_gmail_service(User_Emails):
    creds = None
    
    if os.path.exists(cur.execute(`SELECT refresh_token FROM User_Emails WHERE email = %s`, (User_Emails,))):
        with open( , 'rb') as token:
            creds = pickle.load(token)
            
    # If there are no valid credentials available, let the user log in safely
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # You download 'credentials.json' from your Google Cloud Console
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open(, 'wb') as token:
            pickle.dump(creds, token)

    return build('gmail', 'v1', credentials=creds)

def login(service , userId):

    """
    Handles the login process for the Gmail API.
    """
    userEmail =  st.text_input("What is your email address?")
    user = service.users().getProfile(userId=userEmail).execute()
    return user 

def scan_inbox_by_batches(service, max_pages=10):
    sender_counts = {}
    page_token = None
    pages_scanned = 0

    def callback(request_id, response, exception):
        if exception is not None:
            return # Ignore errors for single problematic emails
        headers = response.get('payload', {}).get('headers', [])
        for header in headers:
            if header['name'] == 'From':
                sender = header['value']
                sender_counts[sender] = sender_counts.get(sender, 0) + 1
    
    print("Starting secure pipeline scan...")
    
    # We loop by pages so we don't crash our system or violate rate limits
    while pages_scanned < max_pages:
        # Fetch a list of message IDs from the 'Promotions' or 'Updates' categories
        results = service.users().messages().list(
            userId='me', 
            q='category:promotions', # Targets clutter directly
            maxResults=100, 
            pageToken=page_token
        ).execute()
        
        messages = results.get('messages', [])
        if not messages:
            break

        # Create a single batch container for this page
        batch = service.new_batch_http_request(callback=callback)
            
        # For each message ID, fetch the actual Header details
        for msg in messages:
            batch.add(service.users().messages().get(userId='me', id=msg['id'], format='metadata', metadataHeaders=['From']))
        
        # Execute the batch request
        batch.execute()
        
        # Move to the next 100 emails
        page_token = results.get('nextPageToken')
        pages_scanned += 1
        print(f"Scanned page {pages_scanned} ({pages_scanned * 100} emails total)...")
        
        if not page_token:
            break
            
    return sender_counts
def trash_email(service, message_id):
        """
    Moves a specific email message to the trash folder.
    Matches the 'users.messages.trash' REST API method.
    """
        try:
            service.users().messages().trash(userId='me', id=message_id).execute()
            print(f"Email with ID {message_id} has been moved to trash.")
       
        except Exception as e:
            print(f"An error occurred while trying to trash email with ID {message_id}: {e}")


def prompt_user_for_cleanup(service, raw_data):
     # Put it into a Pandas DataFrame for analytics
    if st.button("🚀 Run Secure Inbox Scan (1,000 Emails)"):
        with st.spinner("Analyzing your data pipeline..."):
            raw_data = scan_inbox_by_batches(service, max_pages=10)
        df = pd.DataFrame(list(raw_data.items()), columns=['Sender', 'Count']).sort_values(by='Count', ascending=False)
        st.session_state['leaderboard'] = df
   # Display the leaderboard
    if 'leaderboard' in st.session_state:
        st.subheader("📊 Your Top Clutter Senders")
        st.dataframe(st.session_state['leaderboard'].head(10), use_container_width=True)
        
        st.markdown("---")
        st.subheader("🗑️ Deep Clean Execution Window")
   
   
   # print("\n--- TOP SPAM SENDERS FOUND ---")
    #print(df.head(10))
   # print("\n-------------------------------------------")
    
    
    
    # Ask the user which sender they want to trash
    target_sender = st.text_input("\nEnter the email address of the sender you want to trash: ")

# 2. Ask for the date filter option
    print("\nDate Filter Options:")
    print("1. Delete EVERYTHING from this sender")
    print("2. Delete emails Between specific dates (e.g., 2023-01-01 to 2023-12-31)")
    filter_choice = st.radio(
            "Select range profile:",
            ["Delete EVERYTHING from this sender", "Delete emails BETWEEN specific dates"]
        )
    #("Choose an option (1 or 2): ")

    search_query = f"from:{target_sender} category:promotions"

    if "BETWEEN" in filter_choice:
            start_date = st.text_input("Start Date (YYYY/MM/DD):", value="2023/01/01")
            end_date = st.text_input("End Date (YYYY/MM/DD):", value="2023/12/31")
            search_query += f" after:{start_date} before:{end_date}"
            
    st.warning(f"Target payload rule: `{search_query}`")


    #if filter_choice == '2':
     #   start_date = input("Enter the start date (YYYY/MM/DD): ")
     #   end_date = input("Enter the end date (YYYY/MM/DD): ")
      #  search_query += f" after:{start_date} before:{end_date}"

# Destructive execution button
    if st.button("💥 Execute Irreversible Deep Clean"):
            if not target_sender:
                st.error("Please provide a valid sender email domain target.")
            else:
                page_token = None
                total_trashed = 0
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                with st.spinner("Executing pipeline destruction sequences..."):
                    while True:
                        results = service.users().messages().list(
                            userId='me', q=search_query, maxResults=100, pageToken=page_token
                        ).execute()
                        
                        messages_to_delete = results.get('messages', [])
                        if not messages_to_delete:
                            break
                            
                        status_text.text(f"Processing batch processing sequence... Trashed: {total_trashed}")
                        for msg in messages_to_delete:
                            trash_email(service, msg['id'])
                            total_trashed += 1
                            
                        page_token = results.get('nextPageToken')
                        if not page_token:
                            break
                            
                st.success(f"Clean complete! Successfully relocated {total_trashed} items to your trash folder.")
                # Clear session state so it forces a fresh layout update
                del st.session_state['leaderboard']
    # Double-check with the user so they don't accidentally wipe their inbox
  #  confirm = input(f"Are you sure you want to trash all promotional emails from {target_sender}? (yes/no): ")
   # if confirm.lower() == 'yes':
        # Build a search query to find all emails from that sender in the Promotions category
      #  page_token = None
      #  total_trashed = 0

       # while True:

      #      results = service.users().messages().list(userId='me', q=search_query , pageToken=page_token).execute()
            messages_to_delete = results.get('messages', [])
         #   if not messages_to_delete:
                
          #      print("No messages found matching that sender.")
          #      break
          #  else:
           #     print(f"Found {len(messages_to_delete)} messages. Starting deletion...")
                
                # Loop through the specific matching IDs and trash them
            #    for msg in messages_to_delete:
             #       trash_email(service, msg['id'])
             #       total_trashed += 1
             #   page_token = results.get('nextPageToken')
            #    if not page_token:
            #        break

                    
             #   print("Cleanup complete!")
           




# Run the program and print the top spammers
if __name__ == '__main__':
    st.set_page_config(page_title="Email Cleaner Dashboard", layout="centered")
    service = get_gmail_service()
    user_profile = login(service , 'me')
    st.title("🛡️ Gmail Clutter Analyzer & Cleaner")
    st.write("Scan your promotions tab and surgically wipe out massive spam layers.")
    service = get_gmail_service()
    raw_data = scan_inbox_by_batches(service, max_pages=10) # Scans 1,000 items as a trial
    prompt_user_for_cleanup(service, raw_data)

   
 