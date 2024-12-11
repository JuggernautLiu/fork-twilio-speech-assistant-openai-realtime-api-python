from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse
import os
from dotenv import load_dotenv
from constants import TWILIO_CALLBACK_EVENT_STATUS, TWILIO_VOICE_SETTINGS
from log_utils import setup_logger

# Load environment variables
load_dotenv()

# Setup logger
logger = setup_logger("[Twilio_Client]")

# Get Twilio credentials
account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
twilio_phone_number = os.getenv('TWILIO_PHONE_NUMBER')

# Create Twilio client
client = Client(account_sid, auth_token)

def make_call(to_number: str, twiml_url: str, hostname: str, twilio_voice_settings: dict = None):
    """
    Initiate a call using Twilio API
    :param to_number: The phone number to call
    :param twiml_url: URL for TwiML instructions
    :param hostname: The hostname for callback URL
    :param twilio_voice_settings: Voice settings dictionary
    :return: Call SID if successful, None otherwise
    """
    # Log all input parameters
    logger.info("Call Parameters:")
    logger.info(f"To Number: {to_number}")
    logger.info(f"TwiML URL: {twiml_url}")
    logger.info(f"From Number: {twilio_phone_number}")
    logger.info(f"Host Name: {hostname}")
    logger.info(f"Twilio Voice Settings: {twilio_voice_settings}")

    try:
        call = client.calls.create(
            to=to_number,
            from_=twilio_phone_number,
            url=twiml_url,
            status_callback=f"https://{hostname}/call-status",
            status_callback_event=TWILIO_CALLBACK_EVENT_STATUS,
            status_callback_method="POST",
            timeout=twilio_voice_settings.get('CALL_TIMEOUT_SEC', TWILIO_VOICE_SETTINGS['CALL_TIMEOUT_SEC']),
            time_limit=twilio_voice_settings.get('CALL_TIME_LIMIT_SEC', TWILIO_VOICE_SETTINGS['CALL_TIME_LIMIT_SEC']),
            machine_detection=twilio_voice_settings.get('CALL_MACHINE_DETECTION', TWILIO_VOICE_SETTINGS['CALL_MACHINE_DETECTION']),
            record=twilio_voice_settings.get('CALL_RECORD', TWILIO_VOICE_SETTINGS['CALL_RECORD']),
        )
        logger.info(f"Call initiated. Call SID: {call.sid}")
        return call.sid
    except Exception as e:
        logger.error(f"Error making call: {e}")
        return None

def generate_twiml(message="Hello, this is a test call from Twilio!", voice='alice'):
    """
    Generate a simple TwiML response
    :param message: The message to be spoken
    :param voice: The voice to use for text-to-speech
    :return: TwiML response as a string
    """
    response = VoiceResponse()
    response.say(message, voice=voice)
    return str(response)

async def close_call_by_agent(session_id: str) -> None:
    """
    Close the call using Twilio API
    
    Args:
        session_id: session ID (Call SID)
    """
    try:
        call = client.calls(session_id).update(status='completed')
        logger.info(f"Closed call {session_id}")
        return call.sid
    except Exception as e:
        logger.error(f"Error in close_call_by_agent: {e}")
        return None

# Additional Twilio-related functions can be added here as needed
