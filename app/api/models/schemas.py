from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class SearchRequest(BaseModel):
    query: str = Field(..., description="검색 쿼리", min_length=1)
    max_documents: int = Field(3, description="최대 문서 수", ge=1, le=10)
    include_images: bool = Field(True, description="이미지 포함 여부")
    filter_options: Optional[Dict[str, Any]] = Field(None, description="검색 필터 옵션")


class ImageInfo(BaseModel):
    image: str = Field(..., description="Base64 인코딩된 이미지")
    description: Optional[str] = Field(None, description="이미지 설명")
    related_text_ids: Optional[List[int]] = Field(None, description="관련 텍스트 ID 목록")


class ElementInfo(BaseModel):
    id: int = Field(..., description="요소 ID")
    type: str = Field(..., description="요소 유형 (text, image)")
    content_type: Optional[str] = Field(None, description="컨텐츠 유형")
    content: Optional[str] = Field(None, description="텍스트 내용 (텍스트 요소의 경우)")
    summary: Optional[str] = Field(None, description="텍스트 요약 (텍스트 요소의 경우)")
    description: Optional[str] = Field(None, description="이미지 설명 (이미지 요소의 경우)")


class SourceDocument(BaseModel):
    id: str = Field(..., description="문서 ID")
    folder_name: str = Field(..., description="문서 폴더명")
    page_number: str = Field("", description="페이지 번호")
    text: str = Field("", description="텍스트 내용")
    summary: Optional[str] = Field(None, description="페이지 요약")
    searchScore: float = Field(0.0, description="검색 유사도 점수")
    images: Optional[List[ImageInfo]] = Field(None, description="이미지 목록")
    elements: Optional[List[ElementInfo]] = Field(None, description="요소 목록")


class SearchResponse(BaseModel):
    answer: str = Field(..., description="생성된 답변")
    source_documents: List[SourceDocument] = Field([], description="소스 문서 목록")


class DocumentUploadResponse(BaseModel):
    success: bool = Field(..., description="성공 여부")
    message: str = Field(..., description="처리 메시지")
    document_name: str = Field(..., description="문서명")
    pages_processed: int = Field(0, description="처리된 페이지 수")


class DocumentInfo(BaseModel):
    folder_name: str = Field(..., description="문서 폴더명")
    document_type: str = Field(..., description="문서 유형")
    pages_count: int = Field(0, description="페이지 수")
    created_at: Optional[str] = Field(None, description="생성 시간")
    document_summary: Optional[str] = Field(None, description="문서 요약")


class DocumentListResponse(BaseModel):
    documents: List[DocumentInfo] = Field(..., description="문서 목록")
    total_count: int = Field(..., description="총 문서 수")