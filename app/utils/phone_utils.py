import re

def format_phone_number_with_country_code(phone_number: str) -> str:
    """格式化電話號碼，確保包含國碼"""
    # 移除所有非數字字符
    cleaned_number = re.sub(r'\D', '', phone_number)
    
    # 如果號碼以 0 開頭，替換為台灣國碼 +886
    if cleaned_number.startswith('0'):
        cleaned_number = '886' + cleaned_number[1:]
    
    # 如果號碼沒有國碼，添加台灣國碼
    if not cleaned_number.startswith('886'):
        cleaned_number = '886' + cleaned_number
    
    # 添加 + 號
    formatted_number = '+' + cleaned_number
    
    return formatted_number
