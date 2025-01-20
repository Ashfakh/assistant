# AI Voice Chat Assistant

A real-time voice chat application that allows users to interact with an AI assistant through both text and voice interfaces. Built with FastAPI, WebSocket, and integrates with various AI services.

## Features

- Real-time text and voice chat
- Speech-to-text using browser's Web Speech API
- Text-to-speech capabilities
- WebSocket-based communication for real-time responses
- Integration with OpenAI's language models
- Django-based data persistence
- Clean and responsive web interface

## Prerequisites

- Python 3.11 or higher
- Docker and Docker Compose (for containerized setup)
- OpenAI API key
- Deepgram API key (for speech processing)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd assistant
```

2. Create and activate a virtual environment:
```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On macOS/Linux
python -m venv venv
source venv/bin/activate
```

3. Install the required packages:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the root directory with the following variables:
```env
OPENAI_API_KEY=your_openai_api_key
DEEPGRAM_API_KEY=your_deepgram_api_key

# Docker environment settings
POSTGRES_DB=voicechat
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/voicechat
REDIS_URL=redis://localhost:6379
```

## Database and Redis Setup

### Option 1: Using Docker (Recommended)

1. Start the PostgreSQL and Redis containers:
```bash
docker-compose up -d db redis
```

This will:
- Start PostgreSQL on port 5432
- Start Redis on port 6379
- Create persistent volumes for both services
- Set up the database with the credentials specified in docker-compose.yml

2. Initialize the database schema:
```bash
# The application will automatically create tables using Django ORM
# when it first starts up
```

### Option 2: Manual Setup

If you prefer to run PostgreSQL and Redis directly on your machine:

1. Install and start PostgreSQL
2. Create a database named 'voicechat'
3. Install and start Redis server
4. Update the `.env` file with your local connection details

Note: The application uses Django ORM for database operations but is not a full Django project. Database tables will be automatically created on first startup.

## Running the Application

### Option 1: Using Docker

Run the entire application stack:
```bash
docker-compose up
```

### Option 2: Local Development

1. Ensure PostgreSQL and Redis are running (either via Docker or local installation)
2. Start the FastAPI server:
```bash
uvicorn app.main:app --reload
```

3. Access the application at:
```
http://localhost:8000
```

## Docker Commands

Useful Docker commands for managing the application:

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Rebuild containers
docker-compose up -d --build

# Remove volumes (will delete all data)
docker-compose down -v
```

## Usage

1. Allow microphone permissions when prompted by the browser
2. Select your preferred response type:
   - Text Response: Get text-based responses
   - Audio Response: Get spoken responses through text-to-speech

3. Interact with the assistant:
   - Type messages in the text input field
   - Use the microphone button for voice input
   - Press Enter or click Send to submit messages

4. View the conversation history in the chat window

## Dependencies

Key dependencies include:
- FastAPI (0.104.1): Web framework
- Uvicorn (0.24.0): ASGI server
- SQLAlchemy (2.0.23): SQL toolkit and ORM
- Redis (5.0.1): In-memory data store
- Langchain (0.0.350): LLM framework
- OpenAI: AI model integration
- Django: Database ORM and admin interface
- Deepgram SDK (2.12.0): Speech processing

## Troubleshooting

- Ensure all environment variables are properly set
- Check PostgreSQL and Redis services are running
- Verify API keys are valid
- Check browser console for WebSocket connection issues
- Ensure microphone permissions are granted for voice features

## Development

- Use `uvicorn app.main:app --reload` for development with auto-reload
- Check the FastAPI docs at `http://localhost:8000/docs` for API documentation
- Use Django admin interface for database management

## License

[Add your license information here]

## Contributing

[Add contribution guidelines here]
```

This README now provides a comprehensive guide that:
- Lists all major dependencies from your requirements.txt
- Includes setup instructions for PostgreSQL and Redis
- Mentions environment variables needed
- Provides clear installation and usage instructions
- Includes troubleshooting tips
- Matches the actual technology stack shown in your requirements.txt

You may want to customize it further by:
1. Adding specific database setup instructions
2. Including deployment guidelines
3. Adding API documentation
4. Including testing instructions
5. Adding project structure documentation
6. Including contribution guidelines
7. Specifying the license
