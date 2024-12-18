import os
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from app.config import settings
from app.routers import call, twiml
from app.utils.log_utils import setup_logger
from app.services.settings_service import initialize_settings

# 設置日誌
logger = setup_logger("[Main]")

# 創建 FastAPI 應用
app = FastAPI()

# 設置 CORS 中間件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 根據需要設置允許的域
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 包含路由
# TODO : we could design prefix for each router in the future
#app.include_router(call.router, prefix="/api")
#app.include_router(twiml.router, prefix="/api")
app.include_router(call.router)
app.include_router(twiml.router)

@app.on_event("startup")
async def startup_event():
    """應用啟動時執行的事件"""
    logger.info("Application startup")
    #logger.info("Registered routes:")
    #for route in app.routes:
    #    methods = ", ".join(route.methods) if route.methods else "NO METHODS"
    #    logger.info(f"{methods} {route.path}")
    # 在這裡可以初始化一些全局狀態或資源
    await initialize_settings()

@app.on_event("shutdown")
async def shutdown_event():
    """應用關閉時執行的事件"""
    logger.info("Application shutdown")
    # 在這裡可以清理資源

@app.get("/", response_class=HTMLResponse)
async def index_page():
    """首頁路由"""
    return {"message": "Twilio Media Stream Server is running!"}

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Incoming request: {request.method} {request.url}")
    response = await call_next(request)
    return response

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=settings.app_port)
