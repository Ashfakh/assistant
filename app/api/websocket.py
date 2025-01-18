from fastapi import WebSocket, WebSocketDisconnect, Depends
import uuid
import json
from services.transcription_service import TranscriptionService
from services.chat_service import ChatService
from services.audio_service import AudioService

class WebSocketManager:
    def __init__(self):
        self.transcription_service = TranscriptionService()
        self.chat_service = ChatService()
        self.audio_service = AudioService()

    async def handle_websocket(self, websocket: WebSocket):
        print("New WebSocket connection attempt")
        await websocket.accept()
        session_id = str(uuid.uuid4())
        print(f"WebSocket connected: {session_id}")

        try:
            while True:
                try:
                    # Receive message from client
                    message = await websocket.receive()
                    print(f"Received message: {message}")  # Debug log
                    
                    if message["type"] == "websocket.receive":
                        if "bytes" in message:
                            await self.handle_audio_message(websocket, message["bytes"], session_id)
                        elif "text" in message:
                            await self.handle_text_message(websocket, message["text"], session_id)

                except WebSocketDisconnect:
                    print(f"Client disconnected: {session_id}")
                    break  # Exit the loop on disconnect
                except RuntimeError as e:
                    if "Cannot call 'receive' once a disconnect message has been received" in str(e):
                        print(f"Client disconnected (runtime error): {session_id}")
                        break  # Exit the loop on disconnect
                    raise  # Re-raise other runtime errors

        except Exception as e:
            print(f"Error in WebSocket handler: {str(e)}")
            try:
                if websocket.client_state.CONNECTED:  # Only try to close if still connected
                    await websocket.close(code=1011, reason=str(e))
            except:
                pass  # Ignore any errors during close

    async def handle_audio_message(self, websocket: WebSocket, audio_data: bytes, session_id: str):
        print(f"Received audio data: {len(audio_data)} bytes")

        # Transcribe audio to text
        print("Transcribing audio...")
        text = await self.transcription_service.transcribe_audio(audio_data)
        print(f"Transcribed text: {text}")

        # Get response and send as audio
        await self._process_and_send_response(websocket, text, session_id, "audio")

    async def handle_text_message(self, websocket: WebSocket, text: str, session_id: str):
        try:
            # Parse the text message as JSON
            print(f"Received raw text: {text}")
            data = json.loads(text)
            message = data.get("message")
            response_type = data.get("responseType", "text")  # Default to text response

            print(f"Parsed message: {message}, response_type: {response_type}")

            if not message:
                error_message = "No message provided"
                print(f"Error: {error_message}")
                await websocket.send_text(json.dumps({"error": error_message}))
                return

            # Process message and send response
            await self._process_and_send_response(websocket, message, session_id, response_type)

        except json.JSONDecodeError as e:
            print(f"JSON decode error: {str(e)}")
            error_message = "Invalid JSON format"
            await websocket.send_text(json.dumps({"error": error_message}))
        except Exception as e:
            print(f"Error processing message: {str(e)}")
            error_message = f"Error processing message: {str(e)}"
            await websocket.send_text(json.dumps({"error": error_message}))

    async def _process_and_send_response(self, websocket: WebSocket, message: str, session_id: str, response_type: str):
        """Common method to process messages and send responses."""
        try:
            # Get chat response
            print(f"Getting chat response for: {message}")
            response = await self.chat_service.get_chat_response(message, session_id)
            print(f"Chat response received: {response}")

            if response_type == "audio":
                # Convert response to speech
                print("Converting to speech...")
                audio_response = await self.audio_service.text_to_speech(response)
                print(f"Audio response generated: {len(audio_response)} bytes")
                await websocket.send_bytes(audio_response)
            else:
                # Send text response
                print("Sending text response...")
                await websocket.send_text(json.dumps({"response": response}))
            
            print("Response sent to client")

        except Exception as e:
            print(f"Error in process_and_send_response: {str(e)}")
            error_message = f"Error processing response: {str(e)}"
            await websocket.send_text(json.dumps({"error": error_message})) 