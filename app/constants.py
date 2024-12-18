import os
from dotenv import load_dotenv
from enum import Enum

from utils import get_today_formatted_string

# Load environment variables from .env file
load_dotenv()

GLOBAL_PROJECT = os.getenv("GLOBAL_PROJECT")
GLOBAL_PROJECT_INBOUNDCALL_STR = 'InboundCall'
GLOBAL_PROJECT_INBOUNDCALL_ID = 9999999900
GLOBAL_PROJECT_OUTBOUNDCALL_STR = 'OutboundCall'
GLOBAL_PROJECT_OUTBOUNDCALL_ID = 9999999901
GLOBAL_PROJECT_OPENAI_SESSION_UPDATE_CONFIG_ID = 9999999902
GLOBAL_PROJECT_OPENAI_CHAT_COMPLETIONS_CONFIG_ID = 9999999903



GLOBAL_PROJECT_ID = GLOBAL_PROJECT_OUTBOUNDCALL_ID # by default, OutboundCall
if GLOBAL_PROJECT == GLOBAL_PROJECT_OUTBOUNDCALL_STR:
    GLOBAL_PROJECT_ID = GLOBAL_PROJECT_OUTBOUNDCALL_ID
elif GLOBAL_PROJECT == GLOBAL_PROJECT_INBOUNDCALL_STR:
    GLOBAL_PROJECT_ID = GLOBAL_PROJECT_INBOUNDCALL_ID
else:
    GLOBAL_PROJECT_ID = GLOBAL_PROJECT_OUTBOUNDCALL_ID

# Twilio 語音設置
TWILIO_VOICE_SETTINGS = {
    "WELCOME_MESSAGE": "唯 你好",
    "LANGUAGE": "zh-TW",
    "VOICE": "Alice - redirected",
    "INIT_PAUSE_LENGTH_SEC": 0.5,
    "CALL_TIMEOUT_SEC": 30,
    "CALL_TIME_LIMIT_SEC": 300,
    "CALL_MACHINE_DETECTION": "Enable",
    "CALL_RECORD": "False", # TODO: for the future recording requirements
}
TWILIO_CALLBACK_EVENT_STATUS = [
    "initiated",   # The call has been created and is ready to be initiated
    "ringing",     # The call is currently ringing at the destination
    "answered",    # The call was answered by the recipient
    "completed",   # The call has completed successfully
    "busy",        # The recipient's line was busy
    "no-answer",   # The recipient did not answer the call
    "failed",      # The call could not be completed as dialed
    "canceled"     # The call was canceled before it was answered
]
TWILIO_STATUS_ANSWEREDBY = [
    "human",        # Call answered by a human
    "machine",      # Call answered by an answering machine
    "fax",          # Call answered by a fax machine
    "unknown"       # Unable to determine what answered the call
]

WAITTIME_BEFORE_CALL_function_call_closethecall = 10
DEFAULT_COUNTRY_CODE = "+886"
DEFAULT_TIMEZONE = 'Asia/Taipei'

# OpenAI
OPENAI_MODEL_REALTIME = "gpt-4o-realtime-preview-2024-10-01"
OPENAI_API_URL_REALTIME = "wss://api.openai.com/v1/realtime"
OPENAI_MODEL = "gpt-4o-2024-11-20"
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

# Get current date message
WHAT_DATE_IS_TODAY_PROMPTS = f"[今日日期]\n{get_today_formatted_string()}"


# Just for the Example: chat completions settings
CHAT_COMPLETIONS_SETTINGS_EXAMPLE = {
    "response_format": {
        "type": "json_schema",
        "json_schema": {
            "name": "customer_details_extraction",
            "schema": {
                "type": "object",
                "properties": {
                    "result": {
                        "type": "string", 
                        "description": "Summary of the conversation result"
                    },
                    "callnexttime": {
                        "type": "string",  # Next contact time
                        "description": "Suggested next contact time"
                    },
                    "bookedTime": {
                        "type": "string",  # Customer's appointment time
                        "description": "Customer's specific appointment time"
                    },
                    "customerCount": {
                        "type": "string",  # Number of visitors
                        "description": "Number of visitors for the appointment"
                    },
                    "specialNotes": {
                        "type": "string",  # Additional notes or special requests
                        "description": "Any special requests or additional notes"
                    }
                },
                "required": [
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
