import logging
from fastapi import FastAPI, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

logger = logging.getLogger(__name__)


def create_app(config, search_engine, document_processor):
    """
    FastAPI 애플리케이션 생성

    Args:
        config: 애플리케이션 설정
        search_engine: 검색 엔진 인스턴스
        document_processor: 문서 처리기 인스턴스

    Returns:
        FastAPI 애플리케이션
    """
    app = FastAPI(
        title="통합 문서 검색 API",
        description="GPT-4o 기반 문서 처리 및 검색 API",
        version="1.0.0"
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.config = config
    app.state.search_engine = search_engine
    app.state.document_processor = document_processor

    from api.routes import search, documents

    app.include_router(search.router, prefix="/api", tags=["search"])
    app.include_router(documents.router, prefix="/api", tags=["documents"])

    static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail}
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(f"서버 오류 발생: {exc}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "서버 내부 오류가 발생했습니다."}
        )

    @app.middleware("http")
    async def add_dependencies(request: Request, call_next):
        request.state.config = config
        request.state.search_engine = search_engine
        request.state.document_processor = document_processor
        response = await call_next(request)
        return response

    @app.get("/")
    async def root():
        return {"message": "통합 문서 검색 API에 오신 것을 환영합니다!"}

    @app.get("/health")
    async def health_check():
        status = {
            "status": "online",
            "components": {
                "search_engine": search_engine is not None,
                "document_processor": document_processor is not None,
                "database": search_engine.collection is not None if search_engine else False,
                "openai": search_engine.openai_client is not None if search_engine else False
            }
        }
        return status

    return app