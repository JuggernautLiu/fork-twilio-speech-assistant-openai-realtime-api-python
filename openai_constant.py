import os
from dotenv import load_dotenv
from enum import Enum

# Load environment variables from .env file
load_dotenv()

# OpenAI API settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL_REALTIME = "gpt-4o-realtime-preview-2024-10-01"
OPENAI_API_URL_REALTIME = "wss://api.openai.com/v1/realtime"
OPENAI_MODEL = "gpt-4o-2024-08-06"
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

# System message for the AI assistant
SYSTEM_MESSAGE = (
    "[身份]\n"
    "您是一個線上預約系統的語音助手，是朝居科技房地產預約系統的一部分，專門協助客戶將線上潛在客戶轉換為現場看房預約。\n\n"
    "[語言]\n"
    "請以自然流暢的繁體中文回答。\n\n"
    "[風格]\n"
    "保持專業且有禮貌的語氣。\n"
    "保持簡潔，但要友好和有效率。\n"
    "這是一個語音對話，請保持回應簡短精確，避免過長的敘述。\n"
    "使用輕鬆自然的表達方式，並加入禮貌性的用語，如「請」、「謝謝」和「您」之類的表達．\n"
    "結束通話時請簡短與禮貌的的表達就好，如「謝謝你的時間，再見」\n\n"
    "[回應指導]\n"
    "提供日期和時間時，使用清晰的格式，例如：2024年10月20日星期日。\n"
    "若對話者希望與真人對話，告知「我們稍後會請專員回撥電話」，然後使用 function_call_closethecall 工具結束通話狀態。\n"
    "若對話者表示想要結束通話的意圖，例如['掛斷', '再見', '結束通話', '掰掰', '拜拜', '不用了','Bye']，禮貌地說「謝謝你的時間，再見」，然後使用 function_call_closethecall 工具結束通話狀態。\n\n"
    "[任務]\n"
    "問候對話者，詢問他們想要預約的日期和時間．\n"
    "如果對話者說週幾或是下週幾，例如這週三，請以GMT+8時間，說出明確的日期．\n"
    "與對話者確認完整的預約資訊，包括日期、時間、星期幾，例如：「2024年10月20日星期日」，確保資料無誤。\n"
    "詢問對話者總共幾人一同來訪，並記錄來訪人數。\n"
    "[結束條件]\n"
    "當以下條件之一滿足時，禮貌地說「謝謝你的時間，再見」，並使用 function_call_closethecall 工具結束通話：\n"
    "對話者表示想要結束通話（例如說出'掛斷', '再見', '結束通話' 等）\n"
    "對話者表示希望由真人回撥\n"
)

# Other OpenAI related constants can be added here

SESSION_UPDATE_CONFIG = {
    "type": "session.update",
    "session": {
        "turn_detection": {
            "type": "server_vad",
            "threshold": 0.5,
            "prefix_padding_ms": 300,
            "silence_duration_ms": 300
        },
        "input_audio_format": "g711_ulaw",
        "output_audio_format": "g711_ulaw",
        "voice": "alloy",
        "instructions": SYSTEM_MESSAGE,
        "modalities": ["text", "audio"],
        "temperature": 0.6,
        "input_audio_transcription": {
            "model": "whisper-1"
        },
        "tools": [
            {
                "type": "function",
                "name": "function_call_closethecall",
                "description": "When the user wants to close the call, use this function to close the call",
                "parameters": {}
            }
        ],
        "tool_choice": "auto"
    }
}

class OpenAIEventTypes(str, Enum):
    CONVERSATION_ITEM = "conversation.item"
    RESPONSE_DONE = "response.done"
    RESPONSE_FUNCTION_CALL_ARGUMENTS_DONE = "response.function_call.arguments.done"
    RESPONSE_CONTENT_DONE = 'response.content.done'
    RATE_LIMITS_UPDATED = 'rate_limits.updated'
    AUDIO_BUFFER_COMMITTED = 'input_audio_buffer.committed'
    SPEECH_STOPPED = 'input_audio_buffer.speech_stopped'
    SPEECH_STARTED = 'input_audio_buffer.speech_started'
    SESSION_CREATED = 'session.created'
    RESPONSE_TEXT_DONE = 'response.text.done'
    TRANSCRIPTION_COMPLETED = 'conversation.item.input_audio_transcription.completed'
    CONNECTION_CLOSED = 'connection.closed'
    SESSION_UPDATED = 'session.updated'
    RESPONSE_AUDIO_DELTA = 'response.audio.delta'
    ERROR = 'error'
    RESPONSE_CREATED = 'response.created'
    CONVERSATION_ITEM_CREATED = 'conversation.item.created'
    RESPONSE_FUNCTION_CALL_ARGUMENTS_DELTA = 'response.function_call_arguments.delta'


    
    @classmethod
    def get_all_events(cls) -> list[str]:
        """
        Returns a list of all event type values.
        
        Returns:
            list[str]: List of all OpenAI event type strings
        """
        return [event for event in cls]

# Pre-defined list of all events for easy import
ALL_EVENTS = OpenAIEventTypes.get_all_events()


#SYSTEM_INSTRUCTIONS = "如果對話者有意願預約，與對話者確認完整的預約資訊，包括日期、時間、星期幾，例如：「2024年10月20日星期日」，確保資料無誤，記錄預約日期時間。確認對話者總共來訪人數，並記錄來訪人數，result 記錄為 “RSVPbooked”。如果對話者希望由真人來電，result 記錄為 “humanRequested”，如果對話者目前沒有空，也有提供下次通話時間，result 記錄為 “callNeeded”，記錄時間在callnexttime 。如果對話者表示沒意願，不想預約，result 記錄為 “userRejected”。如果對話者表示打錯電話，result 記錄為 “invalidRecipient”。"
# System instructions for handling real estate viewing appointments
# Timezone: GMT+8 (Taipei)
SYSTEM_INSTRUCTIONS = """
[時區]
GMT+8（台北）
[日期處理]
1. 初始化時的日期同步
   - 每次啟動時，根據系統時間自動設定當前的日期（YYYY-MM-DD 格式）、星期以及時區
   - 例如，若系統時間為 2024-11-18，應同步為：「今天是 2024 年 11 月 18 日，星期一」
2. 模糊時間描述解析
   - 處理用戶常見的模糊描述：
     - 「今天」：當前日期
     - 「明天」：當前日期加一天
     - 「下週一」：以今天為基準，定位到下個星期一的日期
[結構化輸出]
預約情況：
- 與對話者確認完整的預約資訊，包括日期、時間、星期幾
- 範例格式：「2024年11月20日星期三，上午11點」
- 將自然語言日期時間解析為 Supabase 支援的 timestamp 格式（YYYY-MM-DD HH:MM:SS）
- 記錄在 bookedTime
- 確認並記錄來訪人數在 customerCount
- result 記錄為 "RSVPbooked"
其他情況：
- 希望由真人來電：result = "humanRequested"
- 需要改天聯絡：
  - result = "callNeeded"
  - 確認正確的日期
  - 以 timestamp 格式記錄時間在 callnexttime
- 無意願預約：result = "userRejected"
- 打錯電話：result = "invalidRecipient"
"""

# Schema for extracting customer details from conversation
# This schema defines the structure of the response we expect from OpenAI
# It includes fields for:
# - result: Overall conversation result
# - callnexttime: When to follow up with the customer
# - bookedTime: The time slot booked by the customer
# - customerCount: Number of customers in the group
# - specialNotes: Any special requirements or notes
RESPONSE_FORMAT = {
    "response_format": {
        "type": "json_schema",
        "json_schema": {
            "name": "customer_details_extraction",
            "schema": {
                "type": "object",
                "properties": {
                    "result": {
                        "type": "string"  # Overall conversation outcome
                    },
                    "callnexttime": {
                        "type": "string"  # Follow-up call timing
                    },
                    "bookedTime": {
                        "type": "string"  # Customer's booked appointment time
                    },
                    "customerCount": {
                        "type": "string"  # Number of people in the visiting group
                    },
                    "specialNotes": {
                        "type": "string"  # Additional notes or special requirements
                    }
                },
                "required": [  # All fields are required in the response
                    "result",
                    "callnexttime",
                    "bookedTime",
                    "customerCount",
                    "specialNotes"
                ]
            }
        }
    }
}