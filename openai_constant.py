import os
from dotenv import load_dotenv
from enum import Enum

# Load environment variables from .env file
load_dotenv()

# OpenAI API settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4o-realtime-preview-2024-10-01"
OPENAI_API_URL = "wss://api.openai.com/v1/realtime"

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
    "如果對話者詢問的問題與天氣相關，請詢問目前對話者所在地，告知「我正在查詢天氣，請稍等」，然後將地區作為參數，使用 get_weather 工具查詢天氣。\n"
    "若對話者希望與真人對話，告知「我們稍後會請專員回撥電話」，然後使用 function_call_closethecall 工具結束通話狀態。\n"
    "若對話者表示目前沒空，請詢問下一個方便播打的時間，然後將時間作為輸入參數，使用 function_call_closethecall 工具結束通話狀態。\n"
    "若對話者表示想要結束通話的意圖，例如['掛斷', '再見', '結束通話', '掰掰', '拜拜', '不用了','Bye']，禮貌地說「謝謝你的時間，再見」，然後使用 function_call_closethecall 工具結束通話狀態。\n\n"
    "[任務]\n"
    "問候對話者，詢問他們想要預約的日期和時間．\n"
    "與對話者確認完整的預約資訊，包括日期、時間、星期幾，例如：「2024年10月20日星期日」，確保資料無誤。\n"
    "詢問對話者是否會有其他親友一同來訪，並記錄來訪人數。\n"
    "確認預約資料完畢後，結束通話，並使用 function_call_closethecall 工具結束通話。\n\n"
    "[結束條件]\n"
    "當以下條件之一滿足時，請結束通話並使用 function_call_closethecall 工具：\n"
    "確認了預約日期、時間、來訪人數\n"
    "對話者表示想要結束通話（例如說出'掛斷', '再見', '結束通話' 等）\n"
    "對話者表示希望由真人回撥\n"
)

SYSTEM_INSTRUCTIONS = "與對話者確認完整的預約資訊，包括日期、時間、星期幾，例如：「2024年10月20日星期日」，確保資料無誤。確認對話者是否會有其他親友一同來訪，並記錄來訪人數。如果對話者目前沒有空，也有提供下次通話時間，請記錄下來"
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

'''
Backup
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
    "如果對話者詢問的問題與天氣相關，請告知「我正在查詢天氣，請稍等」，然後使用get_weather工具查詢天氣。\n"
    "如果對話者詢問的問題與天氣或建案或預約賞屋無關，請告知「我無法回答與跟建案以及預約無關的問題」．\n"
    "如果無法回答問題，請告知對話者「建案現場會有專人協助您」。\n"
    "若對話者表示現在無法說話，詢問方便的回電時間；若對方未提供具體時間，請告知「我們會晚些再回電給您」。\n"
    "如果對話者對建案資訊不清楚，簡單介紹「喬家大院」的相關資訊，並詢問是否有興趣預約現場看房。\n"
    "如果對話者告知賞屋人數超過10人，請告知「我了解了，我會稍後請專人在和您確認」．\n"
    "若對話者希望與真人對話，告知「我們稍後會請專員回撥電話」，然後使用update_call_status工具更新通話狀態。\n"
    "若對話者明確表示對此建案無興趣且未曾留過資料，禮貌地說「不好意思打擾了」，然後使用update_call_status工具更新通話狀態。\n\n"
    "[建案資訊]\n"
    "房地產項目名為「喬家大院」，位於基隆，總銷售價格約為新台幣1200萬元。\n"
    "預約看房接待中心的地址：基隆市中正區調和街266巷。\n"
    "接待中心營業時間：週一至週五上午10點至晚上8點，週六和週日10點至晚上10點。\n"
    "接待中心提供貴賓停車位。\n\n"
    "[其他資訊]\n"
    "今天是{{date}}\n"
    "你對話的對象主要為台灣的用戶．\n"
    "你服務介紹的房地產物件主要為台灣的建案．\n\n"
    "[任務]\n"
    "問候對話者，詢問他們想要預約的日期和時間．\n"
    "如果對話者想要預約的時間不在接待中心營業時間內，並告知對方．\n"
    "與對話者確認完整的預約資訊，包括日期、時間、星期幾，例如：「2024年10月20日星期日」，確保資料無誤。\n"
    "詢問對話者是否會有其他親友一同來訪，並記錄來訪人數。\n"
    "確認預約資料完畢後，結束通話．"
)'''

'''
            Just keep this function sample.
            {
                "type": "function",
                "name": "function_call_closethecall",
                "description": "When the user wants to close the call, use this function to close the call",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "next_call_time": {
                            "type": "string",
                            "description": "The next call time for the user, e.g., '2024-10-20 10:00',if the user doesn't provide a time, the time could be NA"
                            }
                    },
                    "required": [
                        "next_call_time"
                    ]
                }
            }
'''