from twilio.twiml.voice_response import VoiceResponse, Connect
from twilio.rest import Client

from app.constants import TWILIO_CALLBACK_EVENT_STATUS, TWILIO_VOICE_SETTINGS
from ..config import settings
from ..utils.log_utils import setup_logger

logger = setup_logger("[Twilio_Service]")

client = Client(settings.twilio_account_sid, settings.twilio_auth_token)

def make_call(to_number: str, twiml_url: str, hostname: str, voice_settings: dict) -> str:
    # Log all input parameters
    logger.info("Call Parameters:")
    logger.info(f"To Number: {to_number}")
    logger.info(f"TwiML URL: {twiml_url}")
    logger.info(f"From Number: {settings.twilio_phone_number}")
    logger.info(f"Host Name: {hostname}")
    logger.info(f"Twilio Voice Settings: {voice_settings}")

    try:
        call = client.calls.create(
            to=to_number,
            from_=settings.twilio_phone_number,
            url=twiml_url,
            status_callback=f"https://{hostname}/call-status",
            status_callback_event=TWILIO_CALLBACK_EVENT_STATUS,
            status_callback_method="POST",
            timeout=voice_settings.get('CALL_TIMEOUT_SEC', TWILIO_VOICE_SETTINGS['CALL_TIMEOUT_SEC']),
            time_limit=voice_settings.get('CALL_TIME_LIMIT_SEC', TWILIO_VOICE_SETTINGS['CALL_TIME_LIMIT_SEC']),
            machine_detection=voice_settings.get('CALL_MACHINE_DETECTION', TWILIO_VOICE_SETTINGS['CALL_MACHINE_DETECTION']),
            machine_detection_timeout=3, #TODO hard code for now
            record=voice_settings.get('CALL_RECORD', TWILIO_VOICE_SETTINGS['CALL_RECORD']),
        )
        logger.info(f"Call initiated. Call SID: {call.sid}")
        return call.sid
    except Exception as e:
        logger.error(f"Error making call: {str(e)}")
        return None

def generate_twiml(welcome_message: str, host: str, session_id: str, voice_settings: dict) -> str:
    """生成 TwiML 響應"""
    response = VoiceResponse()
    response.say(
        welcome_message,
        language=voice_settings["LANGUAGE"],
        voice=voice_settings["VOICE"]
    )
    response.pause(length=voice_settings["INIT_PAUSE_LENGTH_SEC"])
    connect = Connect()
    connect.stream(url=f'wss://{host}/media-stream/{session_id}')
    response.append(connect)
    return str(response)

async def close_call_by_agent(call_sid: str) -> None:
    """結束通話"""
    try:
        client.calls(call_sid).update(status='completed')
        logger.info(f"Call {call_sid} has been ended by agent")
    except Exception as e:
        logger.error(f"Error ending call {call_sid}: {str(e)}")
        raise
