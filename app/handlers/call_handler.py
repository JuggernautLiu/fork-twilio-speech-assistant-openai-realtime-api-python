from fastapi.responses import JSONResponse
from app.constants import DEFAULT_TIMEZONE, TWILIO_STATUS_ANSWEREDBY
from ..services.webhook_service import call_webhook_for_call_status, call_webhook_for_call_result
from fastapi import Request
from datetime import datetime
import pytz
from app.utils.log_utils import setup_logger
from ..services.call_service import CallService
from app.utils.phone_utils import format_phone_number_with_country_code
from ..services import twilio_service
from ..constants import TWILIO_VOICE_SETTINGS
from app.config import settings
# 使用 setup_logger
logger = setup_logger(__name__)

TIMEZONE = pytz.timezone(DEFAULT_TIMEZONE)

async def handle_call_status(request: Request):
    """處理 Twilio 通話狀態回調"""
    try:
        form_data = await request.form()
        
        call_sid = form_data.get("CallSid")
        call_status = form_data.get("CallStatus")
        
        logger.info(f"Call Status Update - SID: {call_sid}, Status: {call_status}")
        bool_should_call_webhook = False

        # 使用 call_service 處理業務邏輯
        call_service = CallService()
        
        if call_status == "answered":
            answered_by = form_data.get("AnsweredBy", "unknown")
            bool_should_call_webhook = await call_service.handle_answered_call(call_sid, answered_by)
            
        elif call_status in ["completed", "no-answer", "canceled", "busy", "failed"]:
            bool_should_call_webhook = await call_service.handle_call_completion(
                call_sid, 
                call_status,
                form_data
            )

        if bool_should_call_webhook:
            timestamp = datetime.now(TIMEZONE).isoformat()
            await call_webhook_for_call_status(call_sid, call_status, timestamp)
            
        return JSONResponse(content={"status": "success"})
            
    except Exception as e:
        logger.error(f"Error processing call status: {str(e)}")
        return JSONResponse(content={"status": "error", "message": str(e)})

async def process_call_result(call_sid: str, result: str, transcript: str):
    """處理通話結果"""
    await call_webhook_for_call_result(call_sid, result, transcript) 

async def handle_outbound_call(request: Request):
    """處理外撥通話請求"""
    try:
        # 獲取請求參數
        if request.method == "GET":
            to_number = request.query_params.get("to_number")
            project_id = request.query_params.get("project_id")
        else:  # POST
            body = await request.json()
            to_number = body.get("to_number")
            project_id = body.get("project_id")
            
        # 驗證必要參數
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
            
        try:
            # 格式化電話號碼
            logger.info(f"Original to_number = {to_number}")
            to_number = format_phone_number_with_country_code(to_number)
            logger.info(f"Formatted country code to_number = {to_number}")
        except ValueError as e:
            return JSONResponse(
                content={"message": str(e)},
                status_code=400
            )
            
        # 獲取 TwiML URL
        hostname = request.url.hostname
        #twiml_url = f"https://{hostname}/twiml"
        
        logger.info(f"To Number: {to_number}")
        logger.info(f"Project ID: {project_id}")
        #logger.info(f"TwiML: {twiml_url}")
        
        # 調用 service 處理通話
        call_service = CallService()
        result = await call_service.initiate_outbound_call(
            to_number=to_number,
            project_id=project_id,
            #twiml_url=twiml_url,
            hostname=hostname
        )
        
        return JSONResponse(content=result)
            
    except Exception as e:
        logger.error(f"Error in handle_outbound_call: {str(e)}")
        return JSONResponse(
            content={"message": f"Error processing request: {str(e)}"}, 
            status_code=500
        ) 

async def handle_welcome_call(host: str, session_id: str) -> str:
    call_service = CallService()
    return await call_service.handle_welcome_call(host, session_id)

async def handle_incoming_call(host: str, session_id: str) -> str:
    call_service = CallService()
    return await call_service.handle_incoming_call(host, session_id) 