from typing import Dict, Any
from ..utils.log_utils import setup_logger

logger = setup_logger("[SessionStore]")

class SessionStore:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.temp_session_map = {}
            cls._instance.call_records = {}
            logger.info("SessionStore initialized")
        return cls._instance
    
    @classmethod
    def get_call_sid(cls, session_id: str) -> str:
        logger.info(f"Getting call_sid for session_id: {session_id}")
        return cls._instance.temp_session_map.get(session_id)
    
    @classmethod
    def set_call_sid(cls, session_id: str, call_sid: str):
        cls._instance.temp_session_map[session_id] = call_sid
        logger.info(f"Session mapping added: {session_id} -> {call_sid}")
    
    @classmethod
    def get_call_record(cls, call_sid: str) -> Dict[str, Any]:
        logger.info(f"Getting call_record for call_sid: {call_sid}")
        return cls._instance.call_records.get(call_sid, {})
    
    @classmethod
    def set_call_record(cls, call_sid: str, record: Dict[str, Any]):
        cls._instance.call_records[call_sid] = record
        logger.info(f"Call record added: {call_sid} -> {record}")

    @classmethod
    def clear_session(cls, session_id: str):
        if session_id in cls._instance.temp_session_map:
            del cls._instance.temp_session_map[session_id]
            logger.info(f"Session mapping removed: {session_id}")
        else:
            logger.info(f"Session mapping not found: {session_id}")

    @classmethod
    def clear_call_record(cls, call_sid: str):
        if call_sid in cls._instance.call_records:
            del cls._instance.call_records[call_sid]
            logger.info(f"Call record removed: {call_sid}")
        else:
            logger.info(f"Call record not found: {call_sid}")
