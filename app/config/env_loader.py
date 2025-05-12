import os
import json
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


def load_config():
    """
    환경 변수 및 설정 파일 로드

    Returns:
        전체 설정 정보
    """
    load_dotenv()

    try:
        config_path = os.getenv('CONFIG_PATH', 'config.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        logger.info(f"설정 파일 로드 성공: {config_path}")
    except Exception as e:
        logger.warning(f"설정 파일 로드 실패: {e}")
        config_data = {
            "openai": {
                "api_version": "2025-01-01-preview",
                "multimodal_model": "gpt-4o",
                "text_model": "gpt-4.1"
            },
            "processing": {
                "max_image_width": 1000,
                "max_image_size_kb": 1024,
                "default_compression_quality": 85
            },
            "search": {
                "default_top_k": 3
            }
        }

    config = {
        'openai': {
            'endpoint': os.getenv('AZURE_OPENAI_ENDPOINT'),
            'api_key': os.getenv('AZURE_OPENAI_API_KEY'),
            'api_version': config_data.get('openai', {}).get('api_version', '2025-01-01-preview'),
            'multimodal_model': config_data.get('openai', {}).get('multimodal_model', 'gpt-4o'),
            'chat_model': config_data.get('openai', {}).get('text_model', 'gpt-4.1'),
            'embedding_model': config_data.get('openai', {}).get('embedding_model', 'text-embedding-3-small')
        },
        'cosmos': {
            'connection_string': os.getenv('COSMOS_CONNECTION_STRING',
                                           "mongodb+srv://cosmosadmin:skeppass!A@cosmos-skep-aoai.global.mongocluster.cosmos.azure.com/?tls=true&authMechanism=SCRAM-SHA-256&retrywrites=false&maxIdleTimeMS=120000"),
            'database': os.getenv('COSMOS_DATABASE', 'SKEP_AIPLATFORM_LOCAL'),
            'collection': os.getenv('COSMOS_COLLECTION', 'welfare')
        },
        'processing': config_data.get('processing', {}),
        'search': config_data.get('search', {})
    }

    if not config['openai']['endpoint'] or not config['openai']['api_key']:
        logger.warning("OpenAI 엔드포인트 또는 API 키가 설정되지 않았습니다.")

    if not config['cosmos']['connection_string']:
        logger.warning("Cosmos DB 연결 문자열이 설정되지 않았습니다.")

    return config