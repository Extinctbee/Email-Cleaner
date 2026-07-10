
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
    database.save_user(email, token_filename)

    request.session['email'] = email
    return RedirectResponse("/dashboard")

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    email = request.session.get('email')
    if not email:
        return RedirectResponse("/")
    return templates.TemplateResponse("dashboard.html", {"request": request, "email": email})