import json
import base64

from fastapi import WebSocket

from app.constants import OPENAI_API_URL, OPENAI_API_URL_REALTIME, OPENAI_MODEL, OPENAI_MODEL_REALTIME, WHAT_DATE_IS_TODAY_PROMPTS
from ..config import settings
from ..utils.log_utils import setup_logger
import httpx
from ..services.settings_service import Settings_Init_FromDB
#from ..services.call_service import CallService

logger = setup_logger("[OpenAI_Service]")

async def send_session_update(openai_ws: WebSocket, call_record) -> None:
    try:
        # 獲取並更新配置
        session_config = Settings_Init_FromDB.SESSION_UPDATE_CONFIG.copy()
        session_config["session"]["instructions"] = await get_session_instructions(call_record)
        
        # 轉換為 JSON 並發送
        config_json = json.dumps(session_config)
        logger.info('Sending session update: %s', config_json)
        await openai_ws.send(config_json)
    except Exception as e:
        logger.error(f"Error sending session update: {str(e)}")
        raise

async def get_session_instructions(call_record) -> str:
    """根據 call_sid 組合系統指令"""
    system_message = Settings_Init_FromDB.OpenAI_Init_SYSTEM_MESSAGE
    
    # 直接使用傳入的 call_service 實例
    project_prompts = call_record["project_prompts"]
    
    date_prompts = WHAT_DATE_IS_TODAY_PROMPTS
    
    logger.info(f"System Message: {system_message}")
    logger.info(f"Project Prompts: {project_prompts}")
    logger.info(f"Date Prompts: {date_prompts}")
    
    return f"{system_message}\n{project_prompts}\n{date_prompts}"

async def make_chat_completion(transcript: str) -> dict:
    """調用 OpenAI Chat Completion API"""
    logger.info(f"Making chat completion with transcript: {transcript}")
    try:
        headers = {
            'Authorization': f"Bearer {settings.openai_api_key}",
            'Content-Type': 'application/json'
        }
        
        payload = {
            "model": OPENAI_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": f"{Settings_Init_FromDB.chat_completions_system_instructions}\n{WHAT_DATE_IS_TODAY_PROMPTS}"
                },
                {
                    "role": "user",
                    "content": transcript
                }
            ],#TODO: Need to get twice because of the nested structure
            "response_format": Settings_Init_FromDB.chat_completions_settings.get("response_format", {}).get("response_format", {}) #TODO: Need to get twice because of the nested structure
        }

        logger.info(f"Payload: {json.dumps(payload, indent=2)}")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                OPENAI_API_URL,
                headers=headers,
                json=payload
            )
            logger.info(f"Chat completion response: {response.json()}")
        return response.json()
    except Exception as e:
        logger.error(f"Error in chat completion: {str(e)}")
        raise
