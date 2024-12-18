from uuid import uuid4
from app.constants import TWILIO_STATUS_ANSWEREDBY, TWILIO_VOICE_SETTINGS
from app.services import twilio_service
from app.services.session_store import SessionStore
from app.utils.log_utils import setup_logger
from app.services.supabase_service import get_project_settings
from app.services.settings_service import Settings_Init_FromDB
from app.services.twilio_service import make_call, close_call_by_agent
from app.services.openai_service import make_chat_completion
from app.services.webhook_service import call_webhook_for_call_result, call_webhook_for_call_status
from typing import Dict, Any
import json
from functools import partial
import asyncio
from twilio.rest import Client
from app.config import settings
from app.utils.log_utils import setup_logger

logger = setup_logger(__name__)

class CallService:
    def __init__(self):
        self.call_records: Dict[str, dict] = {}
        self.temp_session_map: Dict[str, str] = {}  # session_id -> call_sid 的映射
        self.client = Client(settings.twilio_account_sid, settings.twilio_auth_token)

    async def initiate_outbound_call(
        self,
        to_number: str,
        project_id: str,
        #twiml_url: str,
        hostname: str
    ) -> dict:
        """發起外撥通話"""
        try:
            # 生成臨時會話 ID
            temp_session_id = str(uuid4())

            # 構建包含臨時會話 ID 的 TwiML URL
            twiml_url = f"https://{hostname}/twiml?session_id={temp_session_id}"
            logger.info(f"TwiML: {twiml_url}")
            #twiml_url = f"{twiml_url}?session_id={temp_session_id}"
            
            # 獲取專案設置
            custom_project_setting = await get_project_settings(project_id)
            project_prompts = custom_project_setting.get('project_prompts', '')
            
            # 獲取事件循環
            loop = asyncio.get_running_loop()
            
            # 將同步的 Twilio API 調用包裝在 run_in_executor 中
            call_sid = await loop.run_in_executor(
                None,  # 使用默認的執行器（ThreadPoolExecutor）
                partial(  # 使用 partial 創建一個新的函數，預設部分參數
                    make_call,  # 要執行的同步函數
                    to_number=to_number,  # parameters
                    twiml_url=twiml_url,  # parameters
                    hostname=hostname,  # parameters
                    voice_settings=Settings_Init_FromDB.twilio_voice_settings  # parameters
                )
            )
            
            if call_sid:
                # 初始化通話記錄，加入 project_prompts
                self.call_records[call_sid] = {
                    "to_number": to_number,
                    "project_id": project_id,
                    "project_prompts": project_prompts,
                    "transcript": [],
                    "parsed_content": {}
                }
                # 儲存臨時會話 ID 和 call_sid 的對應關係
                # self.temp_session_map[temp_session_id] = call_sid
                SessionStore.set_call_sid(temp_session_id, call_sid)
                SessionStore.set_call_record(call_sid, self.call_records[call_sid])
                
                logger.info(f"Current records: {self.call_records}. temp_session_id: {temp_session_id}. call_sid: {call_sid}")
                return {
                    "message": "Call initiated successfully.",
                    "call_sid": call_sid,
                    "temp_session_id": temp_session_id
                }
            else:
                raise Exception("Failed to initiate call")
                
        except Exception as e:
            logger.error(f"Error initiating outbound call: {str(e)}")
            raise e

    def get_call_sid_by_session(self, session_id: str) -> str:
        """根據 session_id 獲取 call_sid"""
        return self.temp_session_map.get(session_id)
    
    async def handle_answered_call(self, call_sid: str, answered_by: str) -> bool:
        """處理已接聽的通話"""
        logger.info(f"Call answered by: {answered_by}")
        
        should_call_webhook = False
        
        if answered_by == TWILIO_STATUS_ANSWEREDBY["machine"]:
            logger.info("Call answered by a voicemail.")
            should_call_webhook = True
        elif answered_by == TWILIO_STATUS_ANSWEREDBY["fax"]:
            logger.info("Call answered by a fax.")
            should_call_webhook = True
            
        return should_call_webhook

    async def handle_call_completion(self, call_sid: str, call_status: str, form_data: dict) -> bool:
        """處理通話完成狀態"""
        if call_status == "completed":
            logger.info(f'handle_call_completion. CallDuration: {form_data.get("CallDuration")}')
        else:
            retry_info = {
                "call_sid": call_sid,
                "status": call_status,
                "to_number": form_data.get("To"),
                "from_number": form_data.get("From")
            }
            logger.info(f"handle_call_completion. call_status is not completed: {retry_info}")
            
        return True

    async def handle_welcome_call(self, host: str, session_id: str) -> str:
        # Generate a new session_id
        #session_id = str(uuid4())
        # Register session_id in CallService
        #self.temp_session_map[session_id] = None
        
        return twilio_service.generate_twiml(
            Settings_Init_FromDB.twilio_voice_settings.get('WELCOME_MESSAGE', TWILIO_VOICE_SETTINGS['WELCOME_MESSAGE']),
            host,
            session_id,
            Settings_Init_FromDB.twilio_voice_settings
        )

    async def handle_incoming_call(self, host: str, session_id: str) -> str:
        return twilio_service.generate_twiml(
            "Please wait while we connect your call to the A. I. voice assistant",
            host,
            session_id,
            TWILIO_VOICE_SETTINGS
        )

    async def process_transcript(self, call_sid: str, transcript: str) -> None:
        """
        處理對話記錄並發送提取的詳細信息
        
        Args:
            call_sid: 通話識別碼
            transcript: 完整對話記錄
        """
        logger.info(f"開始處理通話 {call_sid} 的對話記錄...")
        
        try:
            # 調用 ChatGPT API
            result = await make_chat_completion(transcript)
            logger.info(f'ChatGPT 原始回應: {json.dumps(result, indent=2)}')
       
            parsed_content = None
            if (result.get('choices') and 
                result['choices'][0].get('message') and 
                result['choices'][0]['message'].get('content')):
                
                try:
                    parsed_content = json.loads(result['choices'][0]['message']['content'])
                    logger.info(f'解析後的內容: {json.dumps(parsed_content, indent=2)}')
                    
                except json.JSONDecodeError as parse_error:
                    logger.error(f'解析 ChatGPT 回應的 JSON 時發生錯誤: {str(parse_error)}')
                    
            else:
                logger.warning('ChatGPT API 回應結構異常')

            logger.info(f'更新通話記錄前: {call_sid}')
            # 從 SessionStore 獲取通話記錄
            call_record = SessionStore.get_call_record(call_sid)
            if call_record:
                # 更新通話記錄
                call_record["transcript"].append(transcript)
                if parsed_content:
                    call_record["parsed_content"].update(parsed_content)
                
                # 更新 SessionStore 中的記錄
                SessionStore.set_call_record(call_sid, call_record)
                
                logger.info(f'通話 {call_sid} 的記錄: {json.dumps(call_record, ensure_ascii=False, indent=2)}')
                
                # 調用 webhook
                if parsed_content:
                    logger.info('準備調用 webhook...')
                    await call_webhook_for_call_result(call_sid, parsed_content, transcript)
                    logger.info('webhook 調用完成')
                
                # 清理記錄
                SessionStore.clear_call_record(call_sid)
                logger.info(f"已清理通話 {call_sid} 的記錄")
                
            logger.info(f'更新通話記錄後: {call_sid}')
            
        except Exception as error:
            logger.error(f'處理對話記錄時發生錯誤: {str(error)}')
            raise