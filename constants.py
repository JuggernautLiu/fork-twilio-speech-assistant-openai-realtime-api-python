import os
from dotenv import load_dotenv
from enum import Enum

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


