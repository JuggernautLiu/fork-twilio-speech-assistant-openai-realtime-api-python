import os
import json
import base64
import asyncio
import websockets
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse
from fastapi.websockets import WebSocketDisconnect
from twilio.twiml.voice_response import VoiceResponse, Connect, Say, Stream
from dotenv import load_dotenv
from openai_constant import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_API_URL, SESSION_UPDATE_CONFIG, SYSTEM_MESSAGE

load_dotenv()

# Configuration
PORT = int(os.getenv('PORT', 5050))
LOG_EVENT_TYPES = [
    'response.content.done', 
    'rate_limits.updated',
    'response.done',
    'input_audio_buffer.committed',
    'input_audio_buffer.speech_stopped',
    'input_audio_buffer.speech_started',
    'session.created',
    'response.text.done',
    'conversation.item.input_audio_transcription.completed'
]

app = FastAPI()


if not OPENAI_API_KEY:
    raise ValueError('Missing the OpenAI API key. Please set it in the .env file.')

@app.get("/", response_class=HTMLResponse)
async def index_page():
    return {"message": "Twilio Media Stream Server is running!"}

@app.api_route("/incoming-call", methods=["GET", "POST"])
async def handle_incoming_call(request: Request):
    """Handle incoming call and return TwiML response to connect to Media Stream."""
    response = VoiceResponse()
    # <Say> punctuation to improve text-to-speech flow
    response.say("Please wait while we connect your call to the A. I. voice assistant")
    response.pause(length=1)
    response.say("你好 我是喬家大院的智能語音助理．我們有收到你對喬家大院的案子有興趣，請問我可以協助你預約來現場賞屋嗎？")
    host = request.url.hostname
    connect = Connect()
    connect.stream(url=f'wss://{host}/media-stream')
    response.append(connect)
    return HTMLResponse(content=str(response), media_type="application/xml")

@app.websocket("/media-stream")
async def handle_media_stream(websocket: WebSocket):
    """Handle WebSocket connections between Twilio and OpenAI."""
    print("Client connected")
    await websocket.accept()

    async with websockets.connect(
        f"{OPENAI_API_URL}?model={OPENAI_MODEL}",
        extra_headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "OpenAI-Beta": "realtime=v1"
        }
    ) as openai_ws:
        await send_session_update(openai_ws)
        stream_sid = None

        async def receive_from_twilio():
            """Receive audio data from Twilio and send it to the OpenAI Realtime API."""
            nonlocal stream_sid
            try:
                async for message in websocket.iter_text():
                    data = json.loads(message)
                    if data['event'] == 'media' and openai_ws.open:
                        audio_append = {
                            "type": "input_audio_buffer.append",
                            "audio": data['media']['payload']
                        }
                        await openai_ws.send(json.dumps(audio_append))
                    elif data['event'] == 'start':
                        stream_sid = data['start']['streamSid']
                        print(f"Incoming stream has started {stream_sid}")
                    else:
                        print('Received non-media event:', data['event'])
            except WebSocketDisconnect:
                print("Client disconnected.")
            finally:
                if openai_ws.open:
                    await openai_ws.close()

        async def send_to_twilio():
            """Receive events from the OpenAI Realtime API, send audio back to Twilio."""
            nonlocal stream_sid
            try:
                async for openai_message in openai_ws:
                    response = json.loads(openai_message)
                    # First, check if the event type needs to be logged
                    if response['type'] in LOG_EVENT_TYPES:
                        print(f"Received event: {response['type']}", response)

                    # Then use match-case to handle specific types of responses
                    match response['type']:
                        case 'session.updated':
                            print("Session updated successfully:", response)
                        
                        case 'response.audio.delta' if response.get('delta'):
                            # Audio received from OpenAI
                            try:
                                # Encode the audio payload
                                audio_payload = base64.b64encode(base64.b64decode(response['delta'])).decode('utf-8')
                                # Prepare the audio delta message
                                audio_delta = {
                                    "event": "media",
                                    "streamSid": stream_sid,
                                    "media": {
                                        "payload": audio_payload
                                    }
                                }
                                # Send the audio data back to Twilio
                                await websocket.send_json(audio_delta)
                            except Exception as e:
                                print(f"Error processing audio data: {e}")
                        
                        case 'conversation.item.input_audio_transcription.completed':
                            # User message transcription handling
                            user_message = response['transcript'].strip()
                            # session['transcript'] += f"User: {user_message}\n"
                            print(f"User: {user_message}")
                        
                        case 'response.done':
                            # Agent message handling
                            agent_message = next((content['transcript'] for content in response['response']['output'][0].get('content', [])
                                                  if 'transcript' in content), 'Agent message not found')
                            # session['transcript'] += f"Agent: {agent_message}\n"
                            print(f"Agent: {agent_message}")
                        
                        case _:
                            print(f"Other Case from OpenAI Events: {response['type']}")
                            print("Full response:", response)
            except Exception as e:
                print(f"Error in send_to_twilio: {e}")

        # Concurrently run two asynchronous functions:
        # 1. receive_from_twilio(): Listens for incoming audio data from Twilio
        # 2. send_to_twilio(): Processes responses from OpenAI and sends audio back to Twilio
        # The gather() function allows these two coroutines to run simultaneously,
        # handling bidirectional audio streaming in real-time.
        await asyncio.gather(receive_from_twilio(), send_to_twilio())

async def send_session_update(openai_ws):
    """Send session update to OpenAI WebSocket."""
    print('Sending session update:', json.dumps(SESSION_UPDATE_CONFIG))
    await openai_ws.send(json.dumps(SESSION_UPDATE_CONFIG))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
