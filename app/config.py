from pydantic import BaseModel, Field
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseModel):
    # OpenAI 設定
    openai_api_key: str = Field(
        default_factory=lambda: os.getenv('OPENAI_API_KEY', '')
    )
    
    # Twilio 設定
    twilio_account_sid: str = Field(
        default_factory=lambda: os.getenv('TWILIO_ACCOUNT_SID', '')
    )
    twilio_auth_token: str = Field(
        default_factory=lambda: os.getenv('TWILIO_AUTH_TOKEN', '')
    )
    twilio_phone_number: str = Field(
        default_factory=lambda: os.getenv('TWILIO_PHONE_NUMBER', '')
    )
    
    # Supabase 設定
    supabase_url: str = Field(
        default_factory=lambda: os.getenv('SUPABASE_URL', '')
    )
    supabase_key: str = Field(
        default_factory=lambda: os.getenv('SUPABASE_KEY', '')
    )
    
    # Base URLs 設定
    base_webhook_url: str = Field(
        default_factory=lambda: os.getenv('BASE_WEBHOOK_URL', 'http://0.0.0.0')
    )
    base_webhook_port: int = Field(
        default_factory=lambda: int(os.getenv('BASE_WEBHOOK_PORT', '5051'))
    )
    
    # 全局設定
    global_project: str = Field(
        default_factory=lambda: os.getenv('GLOBAL_PROJECT', 'OutboundCall')
    )
    environment: str = Field(
        default_factory=lambda: os.getenv('ENV', 'local')
    )
    app_port: int = Field(
        default_factory=lambda: int(os.getenv('APP_PORT', '5050'))
    )
    
    class Config:
        validate_assignment = True
        
    @property
    def is_local(self) -> bool:
        return self.environment.lower() == 'local'
    
    @property
    def webhook_url_call_result(self) -> str:
        if self.is_local:
            return f"{self.base_webhook_url}:{self.base_webhook_port}/webhook/call-result"
        return f"{self.base_webhook_url}/webhook/call-result"
    
    @property
    def webhook_url_call_status(self) -> str:
        if self.is_local:
            return f"{self.base_webhook_url}:{self.base_webhook_port}/webhook/call-status"
        return f"{self.base_webhook_url}/webhook/call-status"
    
    def validate_webhook_config(self) -> None:
        if not all([self.base_webhook_url, self.base_webhook_port]):
            raise ValueError("Missing required webhook configuration")
            
# 創建全局設定實例
settings = Settings()
# 驗證 webhook 配置
settings.validate_webhook_config()
