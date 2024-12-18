from ..dependencies.auth import get_id_token
from ..config import settings
from ..utils.log_utils import setup_logger
import httpx
import os

logger = setup_logger("[WebhookService]")

async def call_webhook(url: str, payload: dict) -> None:
    """
    調用 webhook 並處理 Cloud Run 認證
    """
    try:
        headers = {}
        if settings.environment != 'local':
            try:
                # 獲取目標服務的 URL（去除協議前綴）
                target_audience = url.split('://')[-1].split('/')[0]
                id_token = await get_id_token(target_audience)
                headers = {"Authorization": f"Bearer {id_token}"}
                logger.info("Added IAM authentication token")
            except Exception as e:
                logger.error(f"Failed to get IAM token: {str(e)}")
                raise

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=payload,
                headers=headers,
                timeout=30.0
            )
            
            logger.info(f"Webhook response: {response.status_code}")
            if response.status_code != 200:
                logger.error(f"Webhook error: {response.text}")
                
    except Exception as e:
        logger.error(f"Error calling webhook: {str(e)}")
        raise

async def call_webhook_for_call_result(call_sid: str, result: str, transcript: str):
    """處理通話結果的 webhook"""
    payload = {
        "call_id": call_sid,
        "result": result, 
        "transcript": transcript
    }
    
    logger.info(f"Calling result webhook with payload: {payload}")
    await call_webhook(settings.webhook_url_call_result, payload)

async def call_webhook_for_call_status(call_sid: str, status: str, timestamp: str):
    try:
        payload = {
            "call_id": call_sid,
            "status": status, 
            "timestamp": timestamp
        }
        logger.info(f"Calling webhook with payload: {payload}")

        headers = {}
        environment = os.getenv('ENV', 'local')
        if environment != 'local':
            target_audience =settings.webhook_url_call_status.split('://')[-1].split('/')[0]
            id_token = await get_id_token(target_audience)
            headers = {"Authorization": f"Bearer {id_token}"}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.webhook_url_call_status,
                json=payload,
                headers=headers,
                timeout=30.0
            )
            if response.status_code != 200:
                logger.error(f"Webhook error: {response.text}")
                
    except Exception as e:
        logger.error(f"Error calling webhook: {str(e)}")
        raise 