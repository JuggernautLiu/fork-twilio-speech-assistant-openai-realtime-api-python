from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get Twilio credentials
account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
twilio_phone_number = os.getenv('TWILIO_PHONE_NUMBER')

# Create Twilio client
client = Client(account_sid, auth_token)

def make_call(to_number: str, twiml_url: str, from_number: str = None):
    """
    Initiate a call using Twilio API
    :param to_number: The phone number to call
    :param twiml_url: URL for TwiML instructions
    :param from_number: The phone number to use for the call (optional)
    :return: Call SID if successful, None otherwise
    """
     # Print all input parameters
    print(f"Call Parameters:")
    print(f"To Number: {to_number}")
    print(f"TwiML URL: {twiml_url}")
    # print(f"From Number: {from_number if from_number else twilio_phone_number}")
    print(f"From Number: {twilio_phone_number}")

    try:
        
        call = client.calls.create(
            to=to_number,
            from_=from_number or twilio_phone_number, 
            url=twiml_url
        )
        print(f"Call initiated. Call SID: {call.sid}")
        return call.sid
    except Exception as e:
        print(f"Error making call: {e}")
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

# Additional Twilio-related functions can be added here as needed
