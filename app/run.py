import uvicorn
import argparse
from config.env_loader import load_config

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="통합 문서 검색 시스템")
    parser.add_argument('--host', default='0.0.0.0', help='호스트 주소')
    parser.add_argument('--port', type=int, default=8000, help='포트 번호')
    parser.add_argument('--reload', action='store_true', help='자동 재시작 활성화')

    args = parser.parse_args()

    config = load_config()
    print(f"설정 로드 완료: OpenAI 모델={config['openai'].get('chat_model')}")
    print(f"서버 시작 중: http://{args.host}:{args.port}")

    uvicorn.run(
        "api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload
    )