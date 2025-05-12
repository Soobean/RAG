import os
import json
from dotenv import load_dotenv


def load_config():
    """환경 변수 및 설정 파일 로드"""
    load_dotenv()

    try:
        with open('config/config.json', 'r', encoding='utf-8') as f:
            config_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"설정 파일 로드 오류: {e}")
        config_data = {
            "openai": {"api_version": "2025-01-01-preview"},
            "processing": {"max_image_width": 1000}
        }

    return {
        'openai': {
            'endpoint': os.getenv('AZURE_OPENAI_ENDPOINT'),
            'api_key': os.getenv('AZURE_OPENAI_API_KEY'),
            'api_version': config_data['openai'].get('api_version', '2025-01-01-preview'),
            'embedding_model': config_data['openai'].get('embedding_model', 'text-embedding-3-small'),
            'chat_model': config_data['openai'].get('text_model', 'gpt-4.1')
        },
        'cosmos': {
            'connection_string': os.getenv('COSMOS_CONNECTION_STRING'),
            'database': os.getenv('COSMOS_DATABASE', 'SKEP_AIPLATFORM_LOCAL'),
            'collection': os.getenv('COSMOS_COLLECTION', 'welfare')
        },
        'document': {
            'intelligence_endpoint': os.getenv('AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT'),
            'intelligence_key': os.getenv('AZURE_DOCUMENT_INTELLIGENCE_KEY'),
            'layout_model': config_data.get('document_intelligence', {}).get('layout_model', 'prebuilt-layout')
        },
        'processing': config_data.get('processing', {})
    }