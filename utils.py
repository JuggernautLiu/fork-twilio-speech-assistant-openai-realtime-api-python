from datetime import datetime
import pytz

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