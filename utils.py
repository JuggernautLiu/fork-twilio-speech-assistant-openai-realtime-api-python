from datetime import datetime
import pytz
from constants import DEFAULT_COUNTRY_CODE

def get_taipei_date_info():
    """
    獲取台北時區的當前日期信息
    
    Returns:
        tuple: (datetime對象, 星期幾的中文表示)
    """
    weekday_names = {
        0: '一',
        1: '二',
        2: '三',
        3: '四',
        4: '五',
        5: '六',
        6: '日'
    }
    
    taipei_tz = pytz.timezone('Asia/Taipei')
    today = datetime.now(taipei_tz)
    weekday = weekday_names[today.weekday()]
    
    return today, weekday

def get_today_formatted_string():
    """
    格式化今日日期信息為中文字符串
    
    Returns:
        str: 格式化的日期信息
    """
    today, weekday = get_taipei_date_info()
    return f"今天是 {today.year} 年 {today.month} 月 {today.day} 日，星期{weekday}" 

def format_phone_number_with_country_code(phone_number: str) -> str:
    """
    格式化電話號碼，確保包含國碼
    
    Args:
        phone_number (str): 原始電話號碼
        
    Returns:
        str: 格式化後的電話號碼 (例如: +886912345678)
    """
    if not phone_number:
        raise ValueError("電話號碼不能為空")
        
    # 移除所有空格和破折號
    phone_number = phone_number.replace(" ", "").replace("-", "")
    
    # 如果已經有國碼標示(+)，直接返回
    if phone_number.startswith('+'):
        return phone_number
        
    # 如果號碼以 0 開頭，移除第一個 0
    if phone_number.startswith('0'):
        phone_number = phone_number[1:]
    
    # 添加國碼
    return f"{DEFAULT_COUNTRY_CODE}{phone_number}"