import json
import base64
from fastapi import WebSocket
import websockets
from ..config import settings
from ..utils.log_utils import setup_logger
from ..services import openai_service, call_service
from ..services.call_service import CallService
from datetime import datetime
import pytz
from ..constants import DEFAULT_TIMEZONE, OpenAIEventTypes

logger = setup_logger("[WebSocket_Service]")

class WebSocketManager:
    def __init__(self):
        self.stream_sid = None
        self.call_sid = None
        self.all_transcript = ""
        self.pending_close_call = False

    async def handle_twilio_message(self, message: str, websocket_openai: websockets.WebSocketClientProtocol) -> None:
        """處理來自 Twilio 的消息"""
        data = json.loads(message)
        #logger.info(f"Received Twilio message: {data}")
        if data['event'] == 'media':
            if websocket_openai.open:
                audio_append = {
                    "type": "input_audio_buffer.append",
                    "audio": data['media']['payload']
                }
                await websocket_openai.send(json.dumps(audio_append))
                
        elif data['event'] == 'start':
            self.stream_sid = data['start']['streamSid']
            self.call_sid = data['start']['callSid']
            logger.info(f"Stream started - SID: {self.stream_sid}, Call SID: {self.call_sid}")
            
        elif data['event'] == 'stop':
            logger.info(f"Stream stopped: {data.get('stop', {})}")
            await self.handle_connection_close(websocket_openai)

    async def handle_openai_message(self, message: str, websocket_twilio: WebSocket, websocket_openai: websockets.WebSocketClientProtocol) -> None:
        """處理來自 OpenAI 的消息"""
        response = json.loads(message)
        #logger.info(f"Received OpenAI message: {response}")
        
        match response['type']:
            case OpenAIEventTypes.SESSION_UPDATED:
                logger.info("Session updated successfully: %s", response)
                
            case OpenAIEventTypes.RESPONSE_AUDIO_DELTA if response.get('delta'):
                await self.handle_audio_response(response, websocket_twilio)
                
            case OpenAIEventTypes.TRANSCRIPTION_COMPLETED:
                await self.handle_transcription(response)
                
            case OpenAIEventTypes.RESPONSE_DONE:
                await self.handle_response_done(response)
                
            case OpenAIEventTypes.CONVERSATION_ITEM_CREATED:
                await self.handle_conversation_item(response)
                
            case OpenAIEventTypes.ERROR:
                logger.error(f"OpenAI Error: {response.get('error', 'Unknown error')}")

            case OpenAIEventTypes.CONNECTION_CLOSED:
                await self.handle_connection_close(websocket_openai)

            #case _:
                #logger.warning(f"Unhandled event type: {response['type']}")
                #logger.warning(f"Unhandled event response: {response}")
                
    async def handle_audio_response(self, response: dict, websocket_twilio: WebSocket) -> None:
        """處理音頻響應"""
        try:
            audio_payload = base64.b64encode(base64.b64decode(response['delta'])).decode('utf-8')
            audio_delta = {
                "event": "media",
                "streamSid": self.stream_sid,
                "media": {
                    "payload": audio_payload
                }
            }
            await websocket_twilio.send_json(audio_delta)
        except Exception as e:
            logger.error(f"Error processing audio: {str(e)}")

    async def handle_transcription(self, response: dict) -> None:
        """處理轉錄結果"""
        user_message = "User: " + response['transcript'].strip()
        self.all_transcript += user_message + "\n"
        logger.info(f"Transcription: {user_message}")

    async def handle_response_done(self, response: dict) -> None:
        """處理響應完成事件"""
        output = response.get('response', {}).get('output', [])
        if output:
            agent_message = next((
                content.get('transcript') 
                for content in output[0].get('content', [])
                if 'transcript' in content
            ), 'Agent message not found')
            self.all_transcript += "Agent: " + agent_message + "\n"
            logger.info(f"Agent response: {agent_message}")

        if self.pending_close_call:
            logger.info(f"Pending close call: {self.pending_close_call} for call_sid: {self.call_sid}")
            await self.execute_pending_close_call(self.call_sid)

    async def handle_conversation_item(self, response: dict) -> None:
        """處理對話項目"""
        logger.info("Conversation item created")
        item = response.get('item', {})
        if item.get('type') == 'function_call' and item.get('name') == 'function_call_closethecall':
            logger.info(f"Received close call function for {self.call_sid}")
            logger.info("temp stop auto closing")
            #self.pending_close_call = True

    async def handle_connection_close(self, websocket_openai: websockets.WebSocketClientProtocol) -> None:
        """處理連接關閉"""
        
        if self.all_transcript:
            call_sid = self.call_sid
            transcript = self.all_transcript
            service = CallService()
            await service.process_transcript(
                call_sid,
                transcript
            )
            logger.info(f"Transcript processed for call_sid: {self.call_sid}")
            
        if websocket_openai and not websocket_openai.closed:
            await websocket_openai.close()

    async def execute_pending_close_call(self, call_sid: str) -> None:
        """執行掛斷通話"""
        await call_service.close_call_by_agent(call_sid)
        self.pending_close_call = False 
