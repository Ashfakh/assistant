import os
from fastapi import FastAPI, WebSocket, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import django
from django.conf import settings

# Import Django models
from app.api.websocket import WebSocketManager

# Configure Django settings
def configure_django():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.core.settings')
    if not settings.configured:
        django.setup()

# Initialize Django
configure_django()

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
    return templates.TemplateResponse("index.html", {"request": request})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket_manager.handle_websocket(websocket) 