from fastapi import APIRouter, Request
from app.handlers.call_handler import handle_call_status, handle_outbound_call
from app.utils.log_utils import setup_logger
router = APIRouter()
logger = setup_logger(__name__)

@router.post("/call-status")
async def call_status_webhook(request: Request):
    """通話狀態的 webhook 路由"""
    return await handle_call_status(request)

@router.api_route("/makecall", methods=["GET", "POST"])
async def make_outbound_call(request: Request):
    """發起外撥通話的路由"""
    return await handle_outbound_call(request)