import os
import json
import tempfile
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import uvicorn
from dotenv import load_dotenv
from app.core.document_processor import AdvancedDocumentProcessor

# 환경 변수 로드
load_dotenv()

with open('config/config.json', 'r') as f:
    config_data = json.load(f)

config = {
    'openai': {
        'endpoint': os.getenv('AZURE_OPENAI_ENDPOINT'),
        'api_key': os.getenv('AZURE_OPENAI_API_KEY'),
        'api_version': config_data['openai']['api_version'],
        'multimodal_model': config_data['openai']['multimodal_model'],
        'text_model': config_data['openai']['text_model']
    },
    'document_intelligence': {
        'endpoint': os.getenv('AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT'),
        'key': os.getenv('AZURE_DOCUMENT_INTELLIGENCE_KEY')
    },
    'cosmos': {
        'connection_string': os.getenv('COSMOS_CONNECTION_STRING'),
        'database_id': os.getenv('COSMOS_DATABASE'),
        'collection_name': os.getenv('COSMOS_COLLECTION')
    }
}

processor = AdvancedDocumentProcessor(config)


class ChatRequest(BaseModel):
    message: str
    history: List[Dict[str, str]] = []
    include_images: bool = True


class ChatResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]] = []
    related_images: List[Dict[str, str]] = []



app = FastAPI(title="문서 처리 및 검색 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 파일 업로드 API
@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    """문서 업로드 및 처리"""
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in ['.pdf', '.pptx']:
        raise HTTPException(status_code=400, detail="지원되지 않는 파일 형식. PDF 또는 PPTX 파일만 가능합니다.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
        temp_file.write(await file.read())
        temp_file_path = temp_file.name

    try:
        result = processor.process_document(temp_file_path)
        return {
            "success": True,
            "message": f"{result['pages_processed']}개 페이지가 처리되었습니다.",
            "document_name": result["document_name"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"문서 처리 중 오류 발생: {str(e)}")
    finally:
        os.unlink(temp_file_path)



@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """챗봇 대화 처리"""
    try:
        search_results = processor.search_engine.vector_search_all(
            query_text=request.message,
            top_k=config_data['search']['default_top_k']
        )

        if not search_results:
            return ChatResponse(
                answer="질문과 관련된 정보를 찾을 수 없습니다.",
                sources=[],
                related_images=[]
            )

        context = "관련 문서 정보:\n\n"
        sources = []
        related_images = []

        for idx, result in enumerate(search_results):
            folder_name = result.get('folder_name', '')
            page_number = result.get('page_number', '')
            description = result.get('description', '')

            context += f"문서 {idx + 1}: {folder_name} (페이지 {page_number})\n{description}\n\n"

            sources.append({
                "title": folder_name,
                "page": page_number,
                "similarity": result.get("searchScore", 0)
            })

            if request.include_images and 'images' in result:
                for img_idx, img in enumerate(result.get('images', [])[:2]):
                    related_images.append({
                        "image_url": img,
                        "source": f"{folder_name} (페이지 {page_number})",
                        "region": "unknown",
                        "purpose": "general"
                    })

        messages = [
            {
                "role": "system",
                "content": """
                당신은 사내 문서 기반 질의응답 시스템입니다.
                제공된 문서 정보를 기반으로 사용자 질문에 답변하세요.
                이미지가 있는 내용에 대한 질문이면, 관련 이미지를 참조하도록 안내하세요.
                답변은 간결하고 정확하게 작성하세요.
                """
            }
        ]

        for turn in request.history:
            messages.append({"role": "user", "content": turn.get("user", "")})
            if "assistant" in turn:
                messages.append({"role": "assistant", "content": turn.get("assistant", "")})

        messages.append({
            "role": "user",
            "content": f"질문: {request.message}\n\n{context}"
        })

        response = processor.openai_client.chat.completions.create(
            model=config['openai']['text_model'],
            messages=messages,
            temperature=0.7,
            max_tokens=800
        )

        answer = response.choices[0].message.content

        return ChatResponse(
            answer=answer,
            sources=sources,
            related_images=related_images[:8]  # 이미지 제한
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"응답 생성 중 오류 발생: {str(e)}")


# 서버 실행
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)