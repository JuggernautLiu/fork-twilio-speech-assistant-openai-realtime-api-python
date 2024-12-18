from uuid import uuid4
from fastapi import APIRouter, Request, WebSocket
from fastapi.responses import HTMLResponse

from app.services.call_service import CallService
from app.services.websocket_service import WebSocketManager
from app.services.session_store import SessionStore
from ..services import twilio_service
from ..utils.log_utils import setup_logger
from ..constants import OPENAI_MODEL_REALTIME, OPENAI_API_URL_REALTIME
import asyncio
import websockets
from ..config import settings
from ..services import openai_service
from ..handlers import call_handler

router = APIRouter()
logger = setup_logger("[TwiML_Router]")
@router.api_route("/twiml", methods=["GET", "POST"])
async def serve_twiml(request: Request):
    """提供 TwiML 響應"""
    host = request.url.hostname
    session_id = request.query_params.get("session_id")
    logger.info(f"Received request with session_id: {session_id}")
    
    twiml = await call_handler.handle_welcome_call(host, session_id)
    logger.info(f"Sending TwiML response for session_id: {session_id}")
    return HTMLResponse(content=twiml, media_type="application/xml")

@router.api_route("/incoming-call", methods=["GET", "POST"])
async def handle_incoming_call(request: Request):
    """處理來電"""
    host = request.url.hostname
    session_id = str(uuid4()) #TODO incoming call should have session_id
    logger.info(f"handle_incoming_call Session ID: {session_id}")
    twiml = await call_handler.handle_incoming_call(host, session_id)
    return HTMLResponse(content=twiml, media_type="application/xml")

@router.websocket("/media-stream/{session_id}")
async def handle_media_stream(websocket_twilio: WebSocket, session_id: str):
    """處理 WebSocket 媒體流"""
    logger.info(f"WebSocket connection request received")
    logger.info(f"Path session_id: {session_id}")
    
    query_params = dict(websocket_twilio.query_params)
    logger.info(f"Query parameters: {query_params}")
    
    headers = dict(websocket_twilio.headers)
    logger.info(f"Headers: {headers}")
    
    await websocket_twilio.accept()
    logger.info(f"WebSocket connection accepted")
    
    call_sid = SessionStore.get_call_sid(session_id)
    if not call_sid:
        logger.error(f"No call SID found for session ID: {session_id}")
        await websocket_twilio.close()
        return
    
    logger.info(f"Call SID: {call_sid}")

    call_record = SessionStore.get_call_record(call_sid)
    logger.info(f"Call record: {call_record}")
    ws_manager = WebSocketManager()
    
    try:
        async with websockets.connect(
            f"{OPENAI_API_URL_REALTIME}?model={OPENAI_MODEL_REALTIME}",
            extra_headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "OpenAI-Beta": "realtime=v1"
            }
        ) as websocket_openai:
            await openai_service.send_session_update(websocket_openai, call_record)
            
            async def receive_from_twilio():
                try:
                    async for message in websocket_twilio.iter_text():
                        await ws_manager.handle_twilio_message(message, websocket_openai)
                except Exception as e:
                    logger.error(f"Error receiving from Twilio: {str(e)}")
                finally:
                    if websocket_openai.open:
                        await websocket_openai.close()

            async def send_to_twilio():
                try:
                    async for message in websocket_openai:
                        await ws_manager.handle_openai_message(message, websocket_twilio, websocket_openai)
                except Exception as e:
                    logger.error(f"Error sending to Twilio: {str(e)}")
                finally:
                    if websocket_openai.open:
                        await websocket_openai.close()

            await asyncio.gather(receive_from_twilio(), send_to_twilio())
    finally:
        try:
            await websocket_twilio.close()
        except Exception as e:
            logger.error(f"Error closing Twilio WebSocket: {str(e)}")
            
        if 'websocket_openai' in locals():
            try:
                await websocket_openai.close()
            except Exception as e:
                logger.error(f"Error closing OpenAI WebSocket: {str(e)}")
