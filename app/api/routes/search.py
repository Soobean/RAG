import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List, Optional
from ..models.schemas import SearchRequest, SearchResponse,ImageInfo,ElementInfo,SourceDocument

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/search", response_model=SearchResponse)
async def search_documents(request: Request, search_req: SearchRequest):
    """
    문서 검색 및 답변 생성 API
    """
    try:
        search_engine = request.state.search_engine

        search_results = search_engine.search(
            query=search_req.query,
            top_k=search_req.max_documents,
            filter_options=search_req.filter_options
        )

        if not search_results:
            return SearchResponse(
                answer="질문과 관련된 문서를 찾을 수 없습니다.",
                source_documents=[]
            )

        if not search_req.include_images:
            for doc in search_results:
                doc["images"] = []

        answer = search_engine.generate_answer(search_req.query, search_results)

        source_documents = []
        for result in search_results:
            images = []
            if search_req.include_images and "images" in result:
                for img in result["images"]:
                    if isinstance(img, dict):
                        images.append(ImageInfo(
                            image=img.get("image", ""),
                            description=img.get("description", ""),
                            related_text_ids=img.get("related_text_ids", [])
                        ))
                    else:
                        images.append(ImageInfo(
                            image=img,
                            description="이미지"
                        ))

            elements = []
            if "elements" in result:
                for elem in result["elements"]:
                    element_info = ElementInfo(
                        id=elem.get("id", 0),
                        type=elem.get("type", "unknown"),
                        content_type=elem.get("content_type", "")
                    )

                    if elem.get("type") == "text":
                        element_info.content = elem.get("content", "")
                        element_info.summary = elem.get("summary", "")
                    elif elem.get("type") == "image":
                        element_info.description = elem.get("description", "")

                    elements.append(element_info)

            doc = SourceDocument(
                id=result.get("id", ""),
                folder_name=result.get("folder_name", ""),
                page_number=result.get("page_number", ""),
                text=result.get("text", ""),
                summary=result.get("summary", ""),
                searchScore=result.get("searchScore", 0.0),
                images=images,
                elements=elements
            )

            source_documents.append(doc)

        return SearchResponse(
            answer=answer,
            source_documents=source_documents
        )

    except Exception as e:
        logger.error(f"검색 중 오류 발생: {e}")
        raise HTTPException(status_code=500, detail=f"검색 중 오류 발생: {str(e)}")

@router.get("/document/{document_id}")
async def get_document_by_id(request: Request, document_id: str):
    """
    ID로 문서 조회 API
    """
    try:
        search_engine = request.state.search_engine

        documents = search_engine.find_document({"_id": document_id})

        if not documents or len(documents) == 0:
            raise HTTPException(status_code=404, detail=f"문서를 찾을 수 없습니다: {document_id}")

        return documents[0]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"문서 조회 중 오류 발생: {e}")
        raise HTTPException(status_code=500, detail=f"문서 조회 중 오류 발생: {str(e)}")

@router.get("/documents/{folder_name}")
async def get_documents_by_folder(request: Request, folder_name: str):
    """
    폴더명으로 문서 조회 API
    """
    try:
        search_engine = request.state.search_engine

        consolidated_docs = search_engine.find_document({
            "folder_name": folder_name,
            "is_consolidated": True
        })

        if not consolidated_docs or len(consolidated_docs) == 0:
            documents = search_engine.find_document({"folder_name": folder_name}, limit=50)

            if not documents or len(documents) == 0:
                raise HTTPException(status_code=404, detail=f"문서를 찾을 수 없습니다: {folder_name}")

            documents.sort(key=lambda doc: search_engine._safe_int(doc.get("page_number", "0")))

            return {
                "folder_name": folder_name,
                "is_consolidated": False,
                "pages_count": len(documents),
                "pages": documents
            }

        consolidated_doc = consolidated_docs[0]

        return {
            "folder_name": folder_name,
            "is_consolidated": True,
            "document_summary": consolidated_doc.get("document_summary", ""),
            "pages_count": len(consolidated_doc.get("pages", [])),
            "pages": consolidated_doc.get("pages", []),
            "all_images": consolidated_doc.get("all_images", [])[:10]  # 이미지 수 제한
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"문서 조회 중 오류 발생: {e}")
        raise HTTPException(status_code=500, detail=f"문서 조회 중 오류 발생: {str(e)}")