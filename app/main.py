import os
from fastapi import FastAPI, WebSocket, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import django
from django.conf import settings
from asgiref.sync import sync_to_async


# Import Django models

# Configure Django settings
def configure_django():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.core.settings')
    if not settings.configured:
        django.setup()

# Initialize Django
configure_django()

from app.api.websocket import WebSocketManager
from app.models.models import Scheduler


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
    return templates.TemplateResponse("index2.html", {
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

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
    })

# Mock data for reminders
MOCK_REMINDERS = [
    {"id": 1, "title": "Take Medicine", "description": "Daily medication at 9 AM", "due_date": "2024-03-20"},
    {"id": 2, "title": "Doctor Appointment", "description": "Annual checkup", "due_date": "2024-03-25"},
    {"id": 3, "title": "Exercise", "description": "30 minutes walking", "due_date": "2024-03-21"},
]

@app.get("/api/reminders")
async def get_reminders():
    reminders = await sync_to_async(get_reminders_from_db)()
    
    return {"reminders": reminders}

def get_reminders_from_db():
    reminders = Scheduler.objects.all()
    formatted_reminders = [
        {
            "id": reminder.id,
            "title": reminder.schedule_type,
            "description": reminder.schedule_message,
            "due_date": reminder.schedule_time.strftime("%Y-%m-%d"),
            "status": reminder.status
        }
        for reminder in reminders
    ]
    
    return formatted_reminders

MOCK_MOOD_DATA = {
    "timestamp": "2024-03-20T14:30:00Z",
    "overall_mood": "good",
    "energy_level": 8,
    "emotional_state": {
        "happiness": 7,
        "anxiety": 3,
        "irritability": 2,
        "stress": 4
    },
    "physical_state": {
        "pain_level": 2,
        "fatigue": 3,
        "sleep_quality": 8
    },
    "notes": "Dad had a great morning walk and enjoyed breakfast with family. Seems to be in high spirits today.",
    "activities": ["walking", "reading", "family time"],
    "medication_taken": True
}

@app.get("/api/mood")
async def get_mood():
    return MOCK_MOOD_DATA
