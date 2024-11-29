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
from openai_constant import OPENAI_API_KEY, OPENAI_API_URL, OPENAI_MODEL, OPENAI_MODEL_REALTIME, OPENAI_API_URL_REALTIME, SESSION_UPDATE_CONFIG, SYSTEM_INSTRUCTIONS, OpenAIEventTypes, RESPONSE_FORMAT
from twilio_client import make_call, generate_twiml, close_call_by_agent
import requests
from typing import Dict, Any
import traceback
from log_utils import setup_logger
from datetime import datetime
import httpx


load_dotenv()

# Configuration
PORT = int(os.getenv('PORT', 5050))
LOG_EVENT_TYPES = OpenAIEventTypes.get_all_events()
app = FastAPI()
call_sid = None

if not OPENAI_API_KEY:
    raise ValueError('Missing the OpenAI API key. Please set it in the .env file.')

logger = setup_logger("[Twilio_Assistant]")

# Global dictionary to store call information
call_records = {}

# 獲取 webhook URL
BASE_WEBHOOK_URL = os.getenv('BASE_WEBHOOK_URL', 'http://localhost')
BASE_WEBHOOK_PORT = os.getenv('BASE_WEBHOOK_PORT', '5051')
WEBHOOK_URL_CALL_RESULT = f"{BASE_WEBHOOK_URL}:{BASE_WEBHOOK_PORT}/webhook/call-result"
WEBHOOK_URL_CALL_STATUS = f"{BASE_WEBHOOK_URL}:{BASE_WEBHOOK_PORT}/webhook/call-status"

# 驗證設定
if not all([BASE_WEBHOOK_URL, BASE_WEBHOOK_PORT]):
    raise ValueError("Missing required webhook configuration")

# 記錄設定
logger.info(f"Base webhook URL: {BASE_WEBHOOK_URL}")
logger.info(f"Base webhook port: {BASE_WEBHOOK_PORT}")
logger.info(f"Call result webhook URL: {WEBHOOK_URL_CALL_RESULT}")
logger.info(f"Call status webhook URL: {WEBHOOK_URL_CALL_STATUS}")

@app.get("/", response_class=HTMLResponse)
async def index_page():
    return {"message": "Twilio Media Stream Server is running!"}

@app.api_route("/makecall", methods=["GET", "POST"])
async def make_outbound_call(request: Request):
    """Initiate an outbound call when this endpoint is called."""
    try:
        if request.method == "GET":
            to_number = request.query_params.get("to_number")
            project_id = request.query_params.get("project_id")
        else:  # POST
            body = await request.json()
            to_number = body.get("to_number")
            project_id = body.get("project_id")
        
        if not to_number:
            return JSONResponse(
                content={"message": "Missing required parameter: to_number"}, 
                status_code=400
            )
        if not project_id:
            return JSONResponse(
                content={"message": "Missing required parameter: project_id"}, 
                status_code=400
            )
        
        hostname = request.url.hostname
        twiml_url = f"https://{hostname}/twiml"
        
        logger.info(f"To Number: {to_number}")
        logger.info(f"Project ID: {project_id}")
        logger.info(f"TwiML: {twiml_url}")
        
        call_sid = make_call(to_number, twiml_url, hostname)
        
        if call_sid:
            # Initialize call record
            call_records[call_sid] = {
                "to_number": to_number,
                "project_id": project_id,
                "transcript": [],  # Store transcription content
                "parsed_content": {},  # Store parsed results
                "created_at": datetime.now().isoformat()
            }
            
            logger.info(f"Current records: {call_records}")
            return JSONResponse(content={
                #"message": f"Call initiated successfully. Call SID: {call_sid}",
                "message": f"Call initiated successfully.",
                "call_sid": call_sid
            })
        else:
            return JSONResponse(
                content={"message": "Failed to initiate call."}, 
                status_code=500
            )
            
    except Exception as e:
        logger.error(f"Error in make_outbound_call: {str(e)}")
        return JSONResponse(
            content={"message": f"Error processing request: {str(e)}"}, 
            status_code=500
        )

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
    logger.info("Client connected")
    await websocket.accept()
    
    # Initialize stream_sid, call_sid
    stream_sid = None
    call_sid = None
    
    # Initialize user transcriptions for this session
    all_transcript = ""

    async with websockets.connect(
        f"{OPENAI_API_URL_REALTIME}?model={OPENAI_MODEL_REALTIME}",
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
                        logger.info(f"Incoming stream started - Stream SID: {stream_sid}, Call SID: {call_sid}")
                    elif data['event'] == 'mark':
                        # Handle mark events which may indicate call termination
                        logger.info(f"Received mark event: {data.get('mark', {})}")
                        if data.get('mark', {}).get('name') == 'hangup':
                            logger.info("[receive_from_twilio] Call ended by user")
                            break  # Exit the loop when call ends
                    elif data['event'] == 'stop':
                        # Handle stream termination event
                        logger.info(f"[receive_from_twilio] Stream stopped: {data.get('stop', {})}")
                        #logger.info(f"[receive_from_twilio] user_transcript: {all_transcript}")
                        await on_connection_close(openai_ws, stream_sid, all_transcript, call_sid)
                        break  # Exit the loop when stream ends
                    #else:
                        # Log any other non-media events for debugging
                    #    print('[receive_from_twilio] Received non-media event:', data['event'])
            except WebSocketDisconnect:
                logger.info("[receive_from_twilio] Client disconnected.")
            finally:
                # Ensure OpenAI WebSocket is closed
                if openai_ws.open:
                    logger.info("[receive_from_twilio] Closing OpenAI connection")
                    await openai_ws.close()

        async def send_to_twilio():
            """Receive events from the OpenAI Realtime API, send audio back to Twilio."""
            nonlocal stream_sid, call_sid, all_transcript
            try:
                async for openai_message in openai_ws:
                    response = json.loads(openai_message)
                    # First, check if the event type needs to be logged
                    #if response['type'] in LOG_EVENT_TYPES:
                    #    logger.info(f"Received event: {response['type']}")

                    # Then use match-case to handle specific types of responses
                    match response['type']:
                        case OpenAIEventTypes.SESSION_UPDATED:
                            logger.info("Session updated successfully: %s", response)
                        
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
                                logger.error(f"Error processing audio data: {e}")
                        
                        case OpenAIEventTypes.TRANSCRIPTION_COMPLETED:
                            # User message transcription handling
                            user_message = "User: " + response['transcript'].strip()
                            all_transcript += user_message + "\n"
                            logger.info(f"User: {user_message}")
                            # Check if the user wants to hang up
                            hang_up_keywords = ['掛斷', '再見', '結束通話', '掰掰', '拜拜', '不用了', '不需要','Bye']
                            #if any(keyword in user_message for keyword in hang_up_keywords):
                                #print("Detected user request to hang up")
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

                            logger.info(f"Agent: {agent_message}")
                        case OpenAIEventTypes.CONNECTION_CLOSED:
                            logger.info("OpenAI session closed")
                            await openai_ws.close()
                            
                        case OpenAIEventTypes.ERROR:
                            logger.error(f"Error from OpenAI: {response.get('error', 'Unknown error')}")
                            await openai_ws.close()
                            
                        case OpenAIEventTypes.RESPONSE_CREATED:
                            logger.info("Response created")
                            logger.info(response)                            
                        #case OpenAIEventTypes.RESPONSE_FUNCTION_CALL_ARGUMENTS_DELTA:
                        #    logger.info("Response function call arguments delta")
                        #    logger.info(response)
                        case OpenAIEventTypes.RESPONSE_FUNCTION_CALL_ARGUMENTS_DONE:
                            logger.info("Response function call arguments done")
                            logger.info(response)
                            
                        case OpenAIEventTypes.CONNECTION_CLOSED:
                            logger.info("OpenAI connection closed")
                            await openai_ws.close()
                            # Process the complete conversation history here
                            # Optional: Save to database or send to other services
                        case OpenAIEventTypes.CONVERSATION_ITEM_CREATED:
                            logger.info("Conversation item created")
                            item = response.get('item', {})
                            
                            # check if the item is a function call
                            if item.get('type') == 'function_call':
                                function_name = item.get('name')
                                logger.info(f"Function call detected: {function_name}")
                                
                                if function_name == 'function_call_closethecall':
                                    logger.info(f"Executing close call function for call_sid: {call_sid}")
                                    if call_sid:
                                        await asyncio.sleep(2)
                                        await function_call_closethecall(call_sid, "completed")
                                    else:
                                        logger.error("No call_sid available for closing the call")
                        # case _:
                        #    print(f"Other Case from OpenAI Events: {response['type']}")
                        #    print("Full response:", response)
            except Exception as e:
                logger.error(f"Error in send_to_twilio: {str(e)}")
                logger.error(f"Traceback:\n{traceback.format_exc()}")
                
                if openai_ws.open:
                    await openai_ws.close()

        await asyncio.gather(receive_from_twilio(), send_to_twilio())

async def send_session_update(openai_ws):
    """Send session update to OpenAI WebSocket."""
    # TODO:
    # Add the custom prompt based on the project_id
    logger.info('Sending session update: %s', json.dumps(SESSION_UPDATE_CONFIG))
    await openai_ws.send(json.dumps(SESSION_UPDATE_CONFIG))

async def make_chat_gpt_completion(transcript: str) -> Dict[Any, Any]:
    """
    Make a ChatGPT API call to extract customer details from conversation transcript
    
    Args:
        transcript: The conversation transcript text
    
    Returns:
        Dict: Contains extracted customer information
    """
    logger.info('Starting ChatGPT API call...')
    
    try:
        headers = {
            'Authorization': f"Bearer {os.getenv('OPENAI_API_KEY')}",
            'Content-Type': 'application/json'
        }
        
        payload = {
            "model": OPENAI_MODEL,  # Using latest available model
            "messages": [
                {
                    "role": "system", 
                    "content": SYSTEM_INSTRUCTIONS
                },
                {
                    "role": "user",
                    "content": transcript
                }
            ],
            **RESPONSE_FORMAT  # Unpack the schema into the message dictionary
        }
        
        response = requests.post(
            OPENAI_API_URL,
            headers=headers,
            json=payload
        )
        
        logger.info(f'ChatGPT API response status: {response.status_code}')
        data = response.json()
        return data
        
    except Exception as error:
        logger.error(f'Error making ChatGPT completion call: {str(error)}')
        raise error

async def process_transcript_and_send(call_sid: str, transcript: str) -> None:
    """
    Process the conversation transcript and send extracted details
    
    Args:
        transcript: The full conversation transcript
        session_id: Optional session identifier
    """
    #logger.info(f"Starting transcript processing for session {session_id}...")
    
    try:
        # Make the ChatGPT completion call
        result = await make_chat_gpt_completion(transcript)
        logger.info(f'Raw result from ChatGPT: {json.dumps(result, indent=2)}')
   
        if (result.get('choices') and 
            result['choices'][0].get('message') and 
            result['choices'][0]['message'].get('content')):
            
            try:
                parsed_content = json.loads(result['choices'][0]['message']['content'])
                #logger.info(f'Parsed content: {json.dumps(parsed_content, indent=2)}')
                
                if parsed_content:
                    # Send the parsed content to webhook
                    # await send_to_webhook(parsed_content)
                    logger.info(f'Extracted and sent customer details: {parsed_content}')
                else:
                    logger.warning('Unexpected JSON structure in ChatGPT response')
                    
            except json.JSONDecodeError as parse_error:
                logger.error(f'Error parsing JSON from ChatGPT response: {str(parse_error)}')
                
        else:
            logger.warning('Unexpected response structure from ChatGPT API')

        logger.info(f'Before update call_records: {call_sid}')
        if call_sid in call_records:
            # Add transcription content
            call_records[call_sid]["transcript"].append(transcript) 
            call_records[call_sid]["parsed_content"].update(parsed_content)
            logger.info(f'Call record for {call_sid}: {json.dumps(call_records[call_sid],ensure_ascii=False, indent=2)}')
            logger.info(f'before call_webhook_for_call_result')
            await call_webhook_for_call_result(call_sid, parsed_content, transcript)
            logger.info(f'after call_webhook_for_call_result')
            # Clean up record
            del call_records[call_sid]
            logger.info(f"Cleaned up record for call {call_sid}")
        logger.info(f'After update call_records: {call_sid}')
    except Exception as error:
        logger.error(f'Error in process_transcript_and_send: {str(error)}')

# When WebSocket connection is closed
async def on_connection_close(openai_ws, stream_sid: str, all_transcript: str, call_sid: str):
    """Handle WebSocket connection close"""
    try:
        # Close OpenAI WebSocket
        if openai_ws and not openai_ws.closed:
            await openai_ws.close()
            logger.info(f"OpenAI WebSocket closed for stream {stream_sid}")

        # Process final transcript
        if all_transcript:
            logger.info(f"Processing final transcript for call {call_sid}:\n {all_transcript}")
            await process_transcript_and_send(call_sid,all_transcript)
            
    except Exception as e:
        logger.error(f"Error in on_connection_close: {str(e)}")
    
    # Clean up the session

async def function_call_closethecall(call_sid: str, status: str) -> None:
    """Update the status of a call in a session"""
    if not call_sid:
        logger.error("Cannot close call: call_sid is missing")
        return {"status": "error", "message": "call_sid is missing"}

    logger.info(f"Updating call status for call_sid {call_sid} to {status}")
    logger.info("Detected user request to hang up")

    try:
        await close_call_by_agent(call_sid)
        return {"status": "completed"}
    except Exception as e:
        logger.error(f"Error closing call {call_sid}: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.post("/call-status")
async def handle_call_status(request: Request):
    """Handle Twilio call status callback"""
    form_data = await request.form()
    
    call_sid = form_data.get("CallSid")
    call_status = form_data.get("CallStatus")
    
    logger.info(f"Call Status Update - SID: {call_sid}, Status: {call_status}")
    bool_should_call_webhook = False
    if call_status == "initiated":
        logger.info(f"Call {call_sid} has been initiated")
    elif call_status == "ringing":
        logger.info(f"Call {call_sid} is ringing")
    elif call_status == "answered":
        logger.info(f"Call {call_sid} was answered")
    elif call_status == "completed":
        logger.info(f"Call {call_sid} has completed")
        logger.info(f'CallDuration: {form_data.get("CallDuration")}')
        bool_should_call_webhook = True
    elif call_status in ["no-answer", "canceled", "busy", "failed"]:
        retry_info = {
            "call_sid": call_sid,
            "result": "in-progress-noPickup",
            "status": call_status,
            "timestamp": datetime.now().isoformat(),
            "to_number": form_data.get("To"),
            "from_number": form_data.get("From"),
            "retry_count": 1
        }
        bool_should_call_webhook = True
        logger.info(f"Retry info: {retry_info}")
        # TODO: 
        # Call the Webhook to update the call status
    
    if bool_should_call_webhook:
        try:
            timestamp = datetime.now().isoformat()
            payload = {
                "call_id": call_sid,
                "status": call_status, 
                "timestamp": timestamp
            }
            logger.info(f"WEBHOOK_URL_CALL_STATUS: {WEBHOOK_URL_CALL_STATUS}")
            logger.info(f"Calling webhook with payload: {payload}")
            logger.info(f"async with httpx.AsyncClient() as client:")
            async with httpx.AsyncClient() as client:
                response = await client.post(WEBHOOK_URL_CALL_STATUS, json=payload)
                logger.info(f"Webhook response: {response.status_code}")
                if response.status_code != 200:
                    logger.error(f"Webhook error: {response.text}")
                
        except Exception as e:
            logger.error(f"Error calling webhook: {str(e)}")
            
    return JSONResponse(content={"status": "success"})

async def call_webhook_for_call_result(call_sid: str, result: str, transcript: str):
    try:
        payload = {
            "call_id": call_sid,
            "result": result, 
            "transcript": transcript
        }
        logger.info(f"WEBHOOK_URL_CALL_RESULT: {WEBHOOK_URL_CALL_RESULT}")
        logger.info(f"Calling webhook with payload: {payload}")
        logger.info(f"async with httpx.AsyncClient() as client:")
        async with httpx.AsyncClient() as client:
            response = await client.post(WEBHOOK_URL_CALL_RESULT, json=payload)
            logger.info(f"Webhook response: {response.status_code}")
            if response.status_code != 200:
                logger.error(f"Webhook error: {response.text}")
                
    except Exception as e:
        logger.error(f"Error calling webhook: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
