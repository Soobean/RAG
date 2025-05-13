import argparse
import logging
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

import uvicorn
from config.env_loader import load_config
from core.search_engine import DocumentSearchEngine
from core.document_processor import DocumentProcessor
from api.main import create_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="통합 문서 검색 시스템")

    parser.add_argument('--mode', type=str, choices=['api', 'process'], default='api',
                        help='실행 모드 (api: API 서버 실행, process: 문서 처리)')

    parser.add_argument('--host', type=str, default='0.0.0.0', help='API 서버 호스트')
    parser.add_argument('--port', type=int, default=8000, help='API 서버 포트')
    parser.add_argument('--reload', action='store_true', help='자동 재시작 활성화')
    parser.add_argument('--workers', type=int, default=1, help='워커 프로세스 수')

    parser.add_argument('--file', type=str, help='처리할 문서 파일 경로 (process 모드)')

    args = parser.parse_args()

    config = load_config()

    search_engine = DocumentSearchEngine(config)
    document_processor = DocumentProcessor(config, search_engine)

    if args.mode == 'api':
        logger.info(f"API 서버 시작: http://{args.host}:{args.port} (워커 수: {args.workers})")

        app = create_app(config, search_engine, document_processor)

        if args.reload:
            uvicorn.run(
                "run:app",
                host=args.host,
                port=args.port,
                reload=True,
                workers=1
            )
        else:
            uvicorn.run(
                app,
                host=args.host,
                port=args.port,
                workers=args.workers
            )

    elif args.mode == 'process':
        if not args.file:
            logger.error("--file 인자가 필요합니다.")
            return

        logger.info(f"문서 처리 시작: {args.file}")
        try:
            result = document_processor.process_document(args.file)

            if result['status'] == 'success':
                logger.info(f"처리 완료: {result['document_name']}, {result['pages_processed']}페이지")
            else:
                logger.error(f"처리 실패: {result.get('error', '알 수 없는 오류')}")

        except Exception as e:
            logger.error(f"문서 처리 중 오류 발생: {e}")


app = None

if __name__ == "__main__":
    main()
else:
    config = load_config()
    search_engine = DocumentSearchEngine(config)
    document_processor = DocumentProcessor(config, search_engine)
    app = create_app(config, search_engine, document_processor)