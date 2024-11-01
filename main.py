import os
import json
import base64
import asyncio
import websockets
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.websockets import WebSocketDisconnect
from twilio.twiml.voice_response import VoiceResponse, Connect
from dotenv import load_dotenv
from openai_constant import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_API_URL, SESSION_UPDATE_CONFIG, SYSTEM_INSTRUCTIONS, OpenAIEventTypes
from twilio_client import make_call, generate_twiml, close_call_by_agent
import requests
from typing import Dict, Any

load_dotenv()

# Configuration
PORT = int(os.getenv('PORT', 5050))
LOG_EVENT_TYPES = OpenAIEventTypes.get_all_events()
app = FastAPI()

if not OPENAI_API_KEY:
    raise ValueError('Missing the OpenAI API key. Please set it in the .env file.')

@app.get("/", response_class=HTMLResponse)
async def index_page():
    return {"message": "Twilio Media Stream Server is running!"}

@app.api_route("/makecall", methods=["GET", "POST"])
async def make_outbound_call(request: Request):
    """Initiate an outbound call when this endpoint is called."""
    # Example phone number (replace with actual number or get from request)
    to_number = "+886910366640"
    
    # Generate TwiML for the call
    # twiml = generate_twiml("Welcome to our AI assistant. Please hold while we connect you.")
    
    # Save TwiML to a file or host it on a server
    # For this example, let's assume we have a server hosting this TwiML at a specific URL
    twiml_url = f"https://{request.url.hostname}/twiml"
    
    print(f"To Number: {to_number}")
    print(f"TwiML: {twiml_url}")
    # Initiate the call
    call_sid = make_call(to_number, twiml_url)
    
    if call_sid:
        return JSONResponse(content={"message": f"Call initiated successfully. Call SID: {call_sid}"})
    else:
        return JSONResponse(content={"message": "Failed to initiate call."}, status_code=500)
    
@app.api_route("/twiml", methods=["GET", "POST"])
async def serve_twiml(request: Request):
    """Serve TwiML for the outbound call."""
    response = VoiceResponse()
    response.say("Please wait while we connect your call to the A. I. voice assistant")
    response.pause(length=1)
    response.say("Hi Speaking Chinese？")
    host = request.url.hostname
    connect = Connect()
    connect.stream(url=f'wss://{host}/media-stream')
    response.append(connect)
    return HTMLResponse(content=str(response), media_type="application/xml")

@app.api_route("/incoming-call", methods=["GET", "POST"])
async def handle_incoming_call(request: Request):
    """Handle incoming call and return TwiML response to connect to Media Stream."""
    response = VoiceResponse()
    response.say("Please wait while we connect your call to the A. I. voice assistant")
    response.pause(length=1)
    response.say("Hi Speaking Chinese？")
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
    
    # Initialize stream_sid, call_sid
    stream_sid = None
    call_sid = None
    
    # Initialize user transcriptions for this session
    all_transcript = ""

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
            """
            Receive audio data from Twilio and forward it to OpenAI.
            Handles stream initialization and termination.
            """
            nonlocal stream_sid, call_sid
            try:
                async for message in websocket.iter_text():
                    data = json.loads(message)
                    if data['event'] == 'media' and openai_ws.open:
                        # Handle media events by forwarding audio to OpenAI
                        audio_append = {
                            "type": "input_audio_buffer.append",
                            "audio": data['media']['payload']
                        }
                        await openai_ws.send(json.dumps(audio_append))
                    elif data['event'] == 'start':
                        # Get both stream_sid and call_sid from start event
                        stream_sid = data['start']['streamSid']
                        call_sid = data['start']['callSid']
                        print(f"Incoming stream started - Stream SID: {stream_sid}, Call SID: {call_sid}")
                    elif data['event'] == 'mark':
                        # Handle mark events which may indicate call termination
                        print(f"Received mark event: {data.get('mark', {})}")
                        if data.get('mark', {}).get('name') == 'hangup':
                            print("[receive_from_twilio] Call ended by user")
                            break  # Exit the loop when call ends
                    elif data['event'] == 'stop':
                        # Handle stream termination event
                        print(f"[receive_from_twilio] Stream stopped: {data.get('stop', {})}")
                        print(f"[receive_from_twilio] user_transcript: {all_transcript}")
                        await on_connection_close(openai_ws, stream_sid, all_transcript)
                        break  # Exit the loop when stream ends
                    else:
                        # Log any other non-media events for debugging
                        print('[receive_from_twilio] Received non-media event:', data['event'])
            except WebSocketDisconnect:
                print("[receive_from_twilio] Client disconnected.")
            finally:
                # Ensure OpenAI WebSocket is closed
                if openai_ws.open:
                    print("[receive_from_twilio] Closing OpenAI connection: Call openai_ws.close()")
                    await openai_ws.close()

        async def send_to_twilio():
            """Receive events from the OpenAI Realtime API, send audio back to Twilio."""
            nonlocal stream_sid
            nonlocal all_transcript
            try:
                async for openai_message in openai_ws:
                    response = json.loads(openai_message)
                    # First, check if the event type needs to be logged
                    #if response['type'] in LOG_EVENT_TYPES:
                        #print(f"Received event: {response['type']}")

                    # Then use match-case to handle specific types of responses
                    match response['type']:
                        case OpenAIEventTypes.SESSION_UPDATED:
                            print("Session updated successfully:", response)
                        
                        case OpenAIEventTypes.RESPONSE_AUDIO_DELTA if response.get('delta'):
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
                        
                        case OpenAIEventTypes.TRANSCRIPTION_COMPLETED:
                            # User message transcription handling
                            user_message = "User: " + response['transcript'].strip()
                            all_transcript += user_message + "\n"
                            print(f"User: {user_message}")
                            # Check if the user wants to hang up
                            hang_up_keywords = ['掛斷', '再見', '結束通話', '掰掰', '拜拜', '不用了', '不需要','Bye']
                            if any(keyword in user_message for keyword in hang_up_keywords):
                                print("Detected user request to hang up")
                                #if call_sid:
                                #    await close_call_by_agent(call_sid)
                        
                        case OpenAIEventTypes.RESPONSE_DONE:
                            # Agent message handling
                            output = response.get('response', {}).get('output', [])
                            if output:
                                agent_message = next((content.get('transcript') for content in output[0].get('content', [])
                                                      if 'transcript' in content), 'Agent message not found')
                                all_transcript += "Agent: " + agent_message + "\n"
                            else:
                                agent_message = 'Agent message not found'

                            print(f"Agent: {agent_message}")
                        case OpenAIEventTypes.CONNECTION_CLOSED:
                            print("OpenAI session closed")
                            await openai_ws.close()
                            
                        case OpenAIEventTypes.ERROR:
                            print(f"Error from OpenAI: {response.get('error', 'Unknown error')}")
                            await openai_ws.close()
                            
                        case OpenAIEventTypes.CONNECTION_CLOSED:
                            print("OpenAI connection closed")
                            await openai_ws.close()
                            # Process the complete conversation history here
                            # Optional: Save to database or send to other services
                        case _:
                            print(f"Other Case from OpenAI Events: {response['type']}")
                            print("Full response:", response)
            except Exception as e:
                print(f"Error in send_to_twilio: {e}")

        await asyncio.gather(receive_from_twilio(), send_to_twilio())

async def send_session_update(openai_ws):
    """Send session update to OpenAI WebSocket."""
    print('Sending session update:', json.dumps(SESSION_UPDATE_CONFIG))
    await openai_ws.send(json.dumps(SESSION_UPDATE_CONFIG))

async def make_chat_gpt_completion(transcript: str) -> Dict[Any, Any]:
    """
    Make a ChatGPT API call to extract customer details from conversation transcript
    
    Args:
        transcript: The conversation transcript text
    
    Returns:
        Dict: Contains extracted customer information
    """
    print('Starting ChatGPT API call...')
    
    try:
        headers = {
            'Authorization': f"Bearer {os.getenv('OPENAI_API_KEY')}",
            'Content-Type': 'application/json'
        }
        
        payload = {
            "model": "gpt-4o-2024-08-06",  # Using latest available model
            "messages": [
                {
                    "role": "system", 
                    #"content": "Extract customer details: name, availability, and any special notes from the transcript."
                    "content": SYSTEM_INSTRUCTIONS
                },
                {
                    "role": "user",
                    "content": transcript
                }
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "customer_details_extraction",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "customerAvailabeTime": {"type": "string"},
                            "customerCount": {"type": "string"},
                            "specialNotes": {"type": "string"}
                        },
                        "required": ["customerAvailabeTime", "customerComingCount", "specialNotes"]
                    }
                }
            }
        }
        
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers=headers,
            json=payload
        )
        
        print(f'ChatGPT API response status: {response.status_code}')
        data = response.json()
        print(f'Full ChatGPT API response: {json.dumps(data, indent=2)}')
        
        return data
        
    except Exception as error:
        print(f'Error making ChatGPT completion call: {str(error)}')
        raise error

async def process_transcript_and_send(transcript: str, session_id: str = None) -> None:
    """
    Process the conversation transcript and send extracted details
    
    Args:
        transcript: The full conversation transcript
        session_id: Optional session identifier
    """
    print(f"Starting transcript processing for session {session_id}...")
    
    try:
        # Make the ChatGPT completion call
        result = await make_chat_gpt_completion(transcript)
        print(f'Raw result from ChatGPT: {json.dumps(result, indent=2)}')
        
        if (result.get('choices') and 
            result['choices'][0].get('message') and 
            result['choices'][0]['message'].get('content')):
            
            try:
                parsed_content = json.loads(result['choices'][0]['message']['content'])
                print(f'Parsed content: {json.dumps(parsed_content, indent=2)}')
                
                if parsed_content:
                    # Send the parsed content to webhook
                    # await send_to_webhook(parsed_content)
                    print(f'Extracted and sent customer details: {parsed_content}')
                else:
                    print('Unexpected JSON structure in ChatGPT response')
                    
            except json.JSONDecodeError as parse_error:
                print(f'Error parsing JSON from ChatGPT response: {str(parse_error)}')
                
        else:
            print('Unexpected response structure from ChatGPT API')
            
    except Exception as error:
        print(f'Error in process_transcript_and_send: {str(error)}')

# When WebSocket connection is closed
async def on_connection_close(openai_ws, session_id: str, transcript: str ) -> None:
    """
    Handle WebSocket connection close
    
    Args:
        websocket: The WebSocket connection
        session_id: The session identifier
    """
    if openai_ws.open:
        print("[on_connection_close] Closing OpenAI connection: Call openai_ws.close()")
        await openai_ws.close()
    print(f'Client disconnected ({session_id}).')
    print('Full Transcript:')
    print(transcript)
    
    await process_transcript_and_send(transcript, session_id)
    
    # Clean up the session

async def update_call_status(session_id: str, status: str) -> None:
    """Update the status of a call in a session"""
    print(f"Updating call status for session {session_id} to {status}")

async def get_weather(location: str) -> None:
    """
    Simple weather function that just prints 'get_weather'
    
    Args:
        location: The location to get weather for (unused in this implementation)
    """
    print("get_weather")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
