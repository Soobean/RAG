"""검색 관련 API 엔드포인트"""
from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List
from ..models.schemas import SearchRequest, SearchResponse, SourceDocument

router = APIRouter(
    prefix="/search",
    tags=["search"],
    responses={404: {"description": "Not found"}},
)


@router.post("/query", response_model=SearchResponse)
async def search_query(request: Request, search_req: SearchRequest):
    """
    문서 검색 및 답변 생성 API
    """
    try:
        search_engine = request.state.search_engine

        search_results = search_engine.search(
            query=search_req.query,
            top_k=search_req.max_documents
        )

        if not search_results:
            return SearchResponse(
                answer="질문과 관련된 문서를 찾을 수 없습니다.",
                source_documents=[],
                images=[]
            )

        answer = search_engine.generate_answer(search_req.query, search_results)

        source_documents = []
        all_images = []

        for result in search_results:
            source_doc = SourceDocument(
                folder_name=result.get("folder_name", ""),
                page_number=result.get("page_number", ""),
                similarity=result.get("searchScore", 0.0),
                key_information=result.get("key_information", "")
            )
            source_documents.append(source_doc)

            if search_req.include_images and "images" in result:
                images = result.get("images", [])
                if images and len(images) > 0:
                    all_images.extend(images[:2])  # 각 문서에서 최대 2개 이미지만 포함

        return SearchResponse(
            answer=answer,
            source_documents=source_documents,
            images=all_images[:8]  # 최대 8개 이미지만 반환
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"검색 중 오류 발생: {str(e)}")


@router.get("/documents/{folder_name}")
async def get_document(request: Request, folder_name: str):
    """
    특정 문서 조회 API
    """
    try:
        search_engine = request.state.search_engine

        filter_query = {"folder_name": folder_name}
        documents = search_engine.find_document(filter_query)

        if not documents:
            raise HTTPException(status_code=404, detail=f"문서를 찾을 수 없습니다: {folder_name}")

        documents.sort(key=lambda doc: search_engine._safe_int(doc.get("page_number", "0")))

        return {"folder_name": folder_name, "pages": len(documents), "documents": documents}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"문서 조회 중 오류 발생: {str(e)}")