from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class SearchRequest(BaseModel):
    query: str = Field(..., description="검색 쿼리", min_length=1)
    max_documents: int = Field(3, description="최대 문서 수", ge=1, le=20)
    include_images: bool = Field(True, description="이미지 포함 여부")

class SourceDocument(BaseModel):
    folder_name: str = Field(..., description="문서 폴더명")
    page_number: str = Field("", description="페이지 번호")
    similarity: float = Field(0.0, description="검색 유사도 점수")
    key_information: str = Field("", description="핵심 정보")

class SearchResponse(BaseModel):
    answer: str = Field(..., description="생성된 답변")
    source_documents: List[SourceDocument] = Field([], description="소스 문서 목록")
    images: List[str] = Field([], description="관련 이미지 목록")

class DocumentUploadResponse(BaseModel):
    success: bool = Field(..., description="성공 여부")
    message: str = Field(..., description="처리 메시지")
    document_name: str = Field(..., description="문서명")

class DocumentInfo(BaseModel):
    folder_name: str = Field(..., description="문서 폴더명")
    type: str = Field(..., description="문서 유형")
    pages: int = Field(0, description="페이지 수")
    created_at: Optional[str] = Field(None, description="생성 시간")

class DocumentListResponse(BaseModel):
    documents: List[DocumentInfo] = Field(..., description="문서 목록")
    total: int = Field(..., description="총 문서 수")