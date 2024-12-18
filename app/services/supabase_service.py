from supabase import create_client, Client
from ..config import settings
from ..utils.log_utils import setup_logger

logger = setup_logger("[Supabase_Service]")

supabase: Client = create_client(settings.supabase_url, settings.supabase_key)

async def get_project_settings(project_id: int) -> dict:
    """獲取項目設置"""
    try:
        columns = ['id', 'project_name', 'project_prompts', 'project_custom_json_settings']
        response = supabase.table('ProjectConfigs') \
            .select(','.join(columns)) \
            .eq('id', project_id) \
            .execute()
        
        if not response.data:
            logger.error(f"未找到項目ID {project_id} 的設置")
            return {}
            
        project_data = response.data[0]
        
        project_settings = {
            'project_name': project_data.get('project_name'),
            'project_prompts': project_data.get('project_prompts'),
            'project_custom_json_settings': project_data.get('project_custom_json_settings')
        }
        
        logger.info(f"成功獲取項目 {project_id} ���設置")
        return project_settings
        
    except Exception as e:
        logger.error(f"獲取項目設置時發生錯誤: {str(e)}")
        return {}
