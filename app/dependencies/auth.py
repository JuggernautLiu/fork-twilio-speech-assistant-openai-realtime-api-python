from fastapi import Request, HTTPException
from google.auth.transport import requests
from google.oauth2 import id_token
import google.auth
from functools import lru_cache
from datetime import datetime, timedelta
from ..utils.log_utils import setup_logger
from ..config import settings

logger = setup_logger("[Auth]")

# 緩存 token 和過期時間
class TokenCache:
    def __init__(self):
        self.token = None
        self.expiry = None

token_cache = TokenCache()

@lru_cache()
async def get_id_token(target_audience: str) -> str:
    """獲取 Google Cloud Run 認證的 ID token"""
    global token_cache
    
    # 檢查緩存的 token 是否有效
    if token_cache.token and token_cache.expiry and datetime.now() < token_cache.expiry:
        return token_cache.token
    
    try:
        auth_req = requests.Request()
        credentials, project = google.auth.default()
        credentials.refresh(auth_req)
        
        token = id_token.fetch_id_token(auth_req, target_audience)
        
        # 更新緩存
        token_cache.token = token
        token_cache.expiry = datetime.now() + timedelta(hours=1)
        
        return token
    except Exception as e:
        logger.error(f"Error getting ID token: {str(e)}")
        raise

async def verify_cloud_run_auth(request: Request):
    """驗證 Cloud Run 的認證中間件"""
    if settings.environment == "local":
        return True
        
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            raise HTTPException(
                status_code=401, 
                detail="Missing authorization header"
            )
            
        if not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=401, 
                detail="Invalid authorization header format"
            )
            
        token = auth_header.split("Bearer ")[-1]
        
        # 在這裡可以添加額外的 token 驗證邏輯
        # 例如驗證 token 的簽名、過期時間等
        
        return True
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=401, 
            detail="Authentication failed"
        )

# 使用示例：
# 在需要認證的路由中添加依賴
"""
@router.get("/protected-route")
async def protected_route(auth: bool = Depends(verify_cloud_run_auth)):
    return {"message": "This is a protected route"}
"""
