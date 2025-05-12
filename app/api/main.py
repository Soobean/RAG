import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config.env_loader import load_config
from core.search_engine import DocumentSearchEngine
from core.document_processor import DocumentProcessor
from api.routes import search, documents

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

config = load_config()

search_engine = DocumentSearchEngine(config)
document_processor = DocumentProcessor(config, search_engine)

app = FastAPI(
    title="통합 문서 검색 API",
    description="문서 처리 및 검색 API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(search.router, prefix="/api")
app.include_router(documents.router, prefix="/api")

@app.middleware("http")
async def add_context(request: Request, call_next):
    request.state.search_engine = search_engine
    request.state.document_processor = document_processor
    response = await call_next(request)
    return response

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"서버 오류 발생: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "서버 내부 오류가 발생했습니다."}
    )

@app.get("/")
async def root():
    return {"message": "통합 문서 검색 API에 오신 것을 환영합니다!"}