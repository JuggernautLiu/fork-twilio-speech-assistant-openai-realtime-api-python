from app.utils.log_utils import setup_logger
import json
from app.constants import (
    GLOBAL_PROJECT_OUTBOUNDCALL_ID,
    GLOBAL_PROJECT_OPENAI_SESSION_UPDATE_CONFIG_ID,
    GLOBAL_PROJECT_OPENAI_CHAT_COMPLETIONS_CONFIG_ID,
    TWILIO_VOICE_SETTINGS,
    WAITTIME_BEFORE_CALL_function_call_closethecall
)
from app.services.supabase_service import get_project_settings

logger = setup_logger(__name__)

class Settings_Init_FromDB:
    OpenAI_Init_SYSTEM_MESSAGE = ""
    SESSION_UPDATE_CONFIG = {}
    twilio_voice_settings = {}
    waittime_before_call_function_call_closethecall = 0
    chat_completions_system_instructions = ""
    chat_completions_settings = {}

async def initialize_settings():
    """初始化全局設置"""
    logger.info("[initialize_settings] >>>")
    
    # 獲取項目設置
    global_project_setting = await get_project_settings(GLOBAL_PROJECT_OUTBOUNDCALL_ID)
    logger.info(f"Global project settings: {json.dumps(global_project_setting, indent=2, ensure_ascii=False)}")
    
    Settings_Init_FromDB.OpenAI_Init_SYSTEM_MESSAGE = global_project_setting.get('project_prompts', '')
    logger.info(f"OpenAI Init System Message: {Settings_Init_FromDB.OpenAI_Init_SYSTEM_MESSAGE}")
    
    global_project_custom_json_settings = global_project_setting.get('project_custom_json_settings') or {}
    logger.info(f"Global project custom JSON settings: {json.dumps(global_project_custom_json_settings, indent=2, ensure_ascii=False)}")
    
    Settings_Init_FromDB.twilio_voice_settings = (global_project_custom_json_settings or {}).get('TWILIO_VOICE_SETTINGS', TWILIO_VOICE_SETTINGS)
    logger.info(f"Twilio voice settings: {json.dumps(Settings_Init_FromDB.twilio_voice_settings, indent=2, ensure_ascii=False)}")
    
    Settings_Init_FromDB.waittime_before_call_function_call_closethecall = (global_project_custom_json_settings or {}).get(
        'WAITTIME_BEFORE_CALL_function_call_closethecall', 
        WAITTIME_BEFORE_CALL_function_call_closethecall
    )
    logger.info(f"Wait time before call function close: {Settings_Init_FromDB.waittime_before_call_function_call_closethecall}")
    
    # Get OpenAI session update config
    global_openai_session_update_config = await get_project_settings(GLOBAL_PROJECT_OPENAI_SESSION_UPDATE_CONFIG_ID)
    logger.info(f"Global OpenAI session update config: {json.dumps(global_openai_session_update_config, indent=2, ensure_ascii=False)}")
    
    Settings_Init_FromDB.SESSION_UPDATE_CONFIG = global_openai_session_update_config.get('project_custom_json_settings', '')
    logger.info(f"Session update config: {json.dumps(Settings_Init_FromDB.SESSION_UPDATE_CONFIG, indent=2, ensure_ascii=False)}")

    # Get OpenAI chat completions settings
    global_openai_chat_completions_settings = await get_project_settings(GLOBAL_PROJECT_OPENAI_CHAT_COMPLETIONS_CONFIG_ID)
    Settings_Init_FromDB.chat_completions_settings = global_openai_chat_completions_settings.get('project_custom_json_settings', '')
    logger.info(f"Global OpenAI chat completions settings: {json.dumps(Settings_Init_FromDB.chat_completions_settings, indent=2, ensure_ascii=False)}")
    
    Settings_Init_FromDB.chat_completions_system_instructions = global_openai_chat_completions_settings.get('project_prompts', '')
    logger.info(f"Chat completions system instructions: {Settings_Init_FromDB.chat_completions_system_instructions}")

    logger.info("[initialize_settings] <<<") 

# 使用設置
voice_settings = Settings_Init_FromDB.twilio_voice_settings 