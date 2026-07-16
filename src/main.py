
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from google_auth_oauthlib.flow import Flow
import sys
sys.path.insert(0, '/app/src')
import database
from src import GmailScript as gmail
import os
from fastapi import Form
from typing import List


app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET", "dev-secret"))

templates = Jinja2Templates(directory="src/templates")

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:8000/callback")

database.init_db()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login")
async def login(request: Request):
    flow = Flow.from_client_secrets_file('credentials.json', scopes=SCOPES, redirect_uri=REDIRECT_URI)
    auth_url, state = flow.authorization_url(prompt='consent', access_type='offline')
    request.session['state'] = state
    return RedirectResponse(auth_url)

@app.get("/callback")
async def callback(request: Request):
    state = request.session.get('state')
    flow = Flow.from_client_secrets_file('credentials.json', scopes=SCOPES, redirect_uri=REDIRECT_URI, state=state)
    authorization_response = str(request.url).replace("http://", "https://")
    flow.fetch_token(authorization_response=authorization_response)

    creds = flow.credentials
    service = gmail.build_service(creds)
    profile = gmail.login(service)
    email = profile['emailAddress']

    token_filename = f"{email}_token.pickle"
    gmail.save_creds(creds, token_filename)
    database.save_user_to_db(email, token_filename)

    request.session['email'] = email
    return RedirectResponse("/dashboard")

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    email = request.session.get('email')
    if not email:
        return RedirectResponse("/")
    creds = gmail.load_creds(email)
    service = gmail.build_service(creds)
    raw_data = gmail.scan_inbox_by_batches(service, max_pages=10)

    senders = [
        {"email": sender, "count": count}
        for sender, count in sorted(raw_data.items(), key=lambda x: x[1], reverse=True)
    ]
    total = sum(s["count"] for s in senders)

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "email": email,
        "senders": senders,
        "total": total,
        "sender_count": len(senders)
    })

@app.post("/trash")
async def trash_senders(request: Request, senders: List[str] = Form(...)):
    email = request.session.get('email')
    if not email:
        return RedirectResponse("/")

    creds = gmail.load_creds(email)
    service = gmail.build_service(creds)

    total_trashed = 0
    for sender in senders:
        total_trashed += gmail.trash_emails_from_sender(service, sender)

    return RedirectResponse(f"/dashboard?trashed={total_trashed}", status_code=303)
#allows user to filter emails by date range
@app.post("/filter")
async def filter_date(request: Request, start_date: str = Form(...), end_date: str = Form(...)):
    email = request.session.get('email')
    if not email:
        return RedirectResponse("/")

    creds = gmail.load_creds(email)
    service = gmail.build_service(creds)
    #puts the filtered emails into messages variable
    messages = gmail.filter_by_date(service, start_date, end_date)
    senders = {}
    #loops through the filtered emails and counts the number of emails from each sender
    batch = service.new_batch_http_request(callback=callback)
    for msg in messages:
        batch.add(service.users().messages().get(userId='me', id=msg['id'], format='metadata', metadataHeaders=['From']))
    batch.execute()
    # Process the results from the batch request
    for sender, count in senders.items():
        senders[sender] = count

    sorted_senders = sorted(senders.items(), key=lambda x: x[1], reverse=True)
    #calculates the total number of emails from the filtered senders
    total = sum(count for _, count in sorted_senders)
    #renders the dashboard template with the filtered senders and their email counts, along with the total number of emails and the date range used for filtering
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "email": email,
        "senders": [{"email": sender, "count": count} for sender, count in sorted_senders],
        "total": total,
        "sender_count": len(sorted_senders),
        "start_date": start_date,
        "end_date": end_date
    })