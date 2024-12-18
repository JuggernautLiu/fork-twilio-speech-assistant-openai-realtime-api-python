import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logger(logger_name: str) -> logging.Logger:
    """設置並返回一個配置好的 logger"""
    logger = logging.getLogger(logger_name)
    
    if not logger.handlers:  # 避免重複添加 handlers
        logger.setLevel(logging.INFO)
        
        # 控制台處理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # 可選：文件處理器
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        file_handler = RotatingFileHandler(
            os.path.join(log_dir, f"{logger_name}.log"),
            maxBytes=10485760,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger
