import os
from fastapi import FastAPI, WebSocket, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import django
from django.conf import settings

# Import Django models

# Configure Django settings
def configure_django():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.core.settings')
    if not settings.configured:
        django.setup()

# Initialize Django
configure_django()

from app.api.websocket import WebSocketManager


app = FastAPI()
templates = Jinja2Templates(directory="templates")
websocket_manager = WebSocketManager()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    # Get role from query parameters, default to 'user' if not specified
    role = request.query_params.get("role", "dad")
    return templates.TemplateResponse("index.html", {
        "request": request,
        "role": role
    })

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # Get query parameters
    session_id = websocket.query_params.get("session_id")
    role = websocket.query_params.get("role", "dad")  # default to 'user' if not specified
    language = websocket.query_params.get("language", "en")  # default to English
    
    if not session_id:
        await websocket.close(code=4000, reason="Missing session_id parameter")
        return
        
    await websocket_manager.handle_websocket(websocket, session_id, role, language)
