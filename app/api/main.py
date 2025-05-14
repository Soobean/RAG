import logging
from fastapi import FastAPI, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse ,FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
import os
import time
from typing import Callable
import json

logger = logging.getLogger(__name__)


def create_app(config, search_engine, document_processor):
    """
    FastAPI 애플리케이션 생성 (2025-05 최신 버전)

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
        version="2.0.0",
        openapi_url="/api/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    cache = {}

    from fastapi.middleware.gzip import GZipMiddleware
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next: Callable):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response

    @app.middleware("http")
    async def cache_middleware(request: Request, call_next: Callable):
        if config.get('performance', {}).get('cache_enabled', False) and request.method == "GET":
            cache_key = f"{request.url.path}?{request.url.query}"

            ttl = config.get('performance', {}).get('cache_ttl_seconds', 3600)

            cached_response = cache.get(cache_key)
            if cached_response:
                timestamp, content, headers = cached_response
                if time.time() - timestamp < ttl:
                    response = Response(
                        content=content,
                        media_type=headers.get("content-type", "application/json")
                    )
                    for key, value in headers.items():
                        if key != "content-type":
                            response.headers[key] = value
                    response.headers["X-Cache"] = "HIT"
                    return response

        response = await call_next(request)

        if config.get('performance', {}).get('cache_enabled',
                                             False) and request.method == "GET" and response.status_code == 200:
            cache_key = f"{request.url.path}?{request.url.query}"
            content = await response.body()
            headers = dict(response.headers)
            cache[cache_key] = (time.time(), content, headers)
            response.headers["X-Cache"] = "MISS"

        return response

    app.state.config = config
    app.state.search_engine = search_engine
    app.state.document_processor = document_processor

    # 라우터 설정
    from api.routes import search, documents

    prefix_v1 = "/api/v1"
    prefix_v2 = "/api/v2"

    app.include_router(search.router, prefix=prefix_v1, tags=["search_v1"])
    app.include_router(documents.router, prefix=prefix_v1, tags=["documents_v1"])

    app.include_router(search.router, prefix="/api", tags=["search"])
    app.include_router(documents.router, prefix="/api", tags=["documents"])

    static_dir = os.path.join(os.path.dirname(__file__), "..", "..", "static")
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail, "code": exc.status_code}
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(f"서버 오류 발생: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "서버 내부 오류가 발생했습니다.", "code": 500}
        )

    @app.middleware("http")
    async def add_dependencies(request: Request, call_next):
        request.state.config = config
        request.state.search_engine = search_engine
        request.state.document_processor = document_processor
        response = await call_next(request)
        return response

    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        return get_swagger_ui_html(
            openapi_url="/api/openapi.json",
            title="통합 문서 검색 API - 문서",
            swagger_js_url="/static/swagger-ui-bundle.js",
            swagger_css_url="/static/swagger-ui.css",
        )

    @app.get("/", include_in_schema=False)
    async def read_index():
        return FileResponse(os.path.join(static_dir, "index.html"))
    async def root():
        return {
            "message": "통합 문서 검색 API에 오신 것을 환영합니다!",
            "version": "2.0.0",
            "documentation": "/docs",
            "health": "/health"
        }

    @app.get("/health")
    async def health_check():
        status_data = {
            "status": "online",
            "time": time.time(),
            "components": {
                "search_engine": search_engine is not None,
                "document_processor": document_processor is not None,
                "database": search_engine.collection is not None if search_engine else False,
                "openai": search_engine.openai_client is not None if search_engine else False
            }
        }

        if search_engine and search_engine.collection:
            try:
                status_data["database_status"] = "connected"
                status_data["document_count"] = search_engine.collection.count_documents({})
            except Exception as e:
                status_data["database_status"] = f"error: {str(e)}"

        return status_data

    @app.get("/api/info")
    async def api_info():
        return {
            "name": "통합 문서 검색 API",
            "version": "2.0.0",
            "models": {
                "search": config.get('openai', {}).get('chat_model', 'gpt-4.1'),
                "embedding": config.get('openai', {}).get('embedding_model', 'text-embedding-3-small'),
                "vision": config.get('openai', {}).get('multimodal_model', 'gpt-4o')
            },
            "features": [
                "PDF 및 PPTX 처리",
                "텍스트 및 이미지 추출",
                "벡터 검색",
                "시맨틱 검색",
                "자연어 질의응답"
            ]
        }

    @app.on_event("startup")
    async def startup_event():
        """
        애플리케이션 시작 시 이벤트 핸들러
        """
        logger.info(f"애플리케이션 시작됨: API 버전 2.0.0")

        if hasattr(app.state, "search_engine"):
            search_engine = app.state.search_engine
            if search_engine is not None and search_engine.collection is not None:
                logger.info(f"데이터베이스 연결됨: {search_engine.database_id}.{search_engine.collection_name}")
            else:
                logger.warning("데이터베이스 연결되지 않음. 일부 기능이 제한될 수 있습니다.")

    return app