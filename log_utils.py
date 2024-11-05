import logging
import sys
from datetime import datetime
from pathlib import Path

def setup_logger(name: str = __name__, log_level: int = logging.DEBUG) -> logging.Logger:
    """
    設置並返回一個配置好的 logger
    
    Args:
        name: logger 名稱
        log_level: 日誌級別
    """
    # 創建 logs 目錄
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # 設置日誌文件名（包含日期）
    log_file = log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.log"
    
    # 創建 logger
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # 如果 logger 已經有處理器，則不重複添加
    if not logger.handlers:
        # 文件處理器
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(log_level)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        
        # 控制台處理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        
        # 添加處理器
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    
    return logger 