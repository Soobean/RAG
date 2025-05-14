import os
import tempfile
import logging
from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form, Query
from typing import List, Optional
from ..models.schemas import DocumentUploadResponse, DocumentListResponse, DocumentInfo

# 로깅 설정
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(request: Request, file: UploadFile = File(...)):
    """
    문서 업로드 및 처리 API

    - PDF 또는 PPTX 파일을 업로드하여 처리
    - 파일은 GPT-4o를 통해 분석되어 텍스트와 이미지로 분리됨
    - 처리된 문서는 검색 가능한 형태로 데이터베이스에 저장됨
    """
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in ['.pdf', '.pptx']:
        raise HTTPException(status_code=400, detail="지원되지 않는 파일 형식. PDF 또는 PPTX 파일만 가능합니다.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
        temp_file.write(await file.read())
        temp_file_path = temp_file.name

    try:
        document_processor = request.state.document_processor
        folder_name = os.path.splitext(file.filename)[0]
        result = document_processor.process_document(temp_file_path, folder_name)

        if result['status'] == 'error':
            raise HTTPException(
                status_code=500,
                detail=result.get('error', '문서 처리 중 오류가 발생했습니다.')
            )

        return DocumentUploadResponse(
            success=True,
            message=f"{result['pages_processed']}개 페이지가 처리되었습니다.",
            document_name=result['document_name'],
            pages_processed=result['pages_processed']
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"문서 처리 중 오류 발생: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"문서 처리 중 오류 발생: {str(e)}")
    finally:
        try:
            os.unlink(temp_file_path)
        except:
            pass


@router.get("/list", response_model=DocumentListResponse)
async def list_documents(
        request: Request,
        limit: int = Query(50, description="최대 결과 수"),
        offset: int = Query(0, description="결과 오프셋"),
        include_consolidated: bool = Query(True, description="통합 문서 포함 여부"),
        include_pages: bool = Query(False, description="개별 페이지 문서 포함 여부")
):
    """
    문서 목록 조회 API
    """
    try:
        search_engine = request.state.search_engine

        query = {}

        if include_consolidated and not include_pages:
            query["is_consolidated"] = True
        elif include_pages and not include_consolidated:
            query["is_consolidated"] = {"$ne": True}

        all_docs = search_engine.find_document(query, limit=limit)

        documents = []
        seen_folders = set()

        for doc in all_docs:
            folder_name = doc.get('folder_name', '')

            if folder_name in seen_folders:
                continue

            seen_folders.add(folder_name)

            if doc.get('is_consolidated', False):
                document_type = "consolidated"
                pages_count = len(doc.get('pages', []))
            else:
                document_type = "single_page"
                pages_count = 1

            created_at = None
            if 'created_at' in doc:
                try:
                    created_at = doc['created_at'].isoformat()
                except:
                    created_at = str(doc['created_at'])

            document_info = DocumentInfo(
                folder_name=folder_name,
                document_type=document_type,
                pages_count=pages_count,
                created_at=created_at,
                document_summary=doc.get('document_summary', '')
            )

            documents.append(document_info)

        return DocumentListResponse(
            documents=documents,
            total_count=len(documents)
        )

    except Exception as e:
        logger.error(f"문서 목록 조회 중 오류 발생: {e}")
        raise HTTPException(status_code=500, detail=f"문서 목록 조회 중 오류 발생: {str(e)}")


@router.post("/consolidate")
async def consolidate_documents(request: Request):
    """
    문서 통합 API

    - 페이지 단위 문서를 문서 단위로 통합
    - 통합 문서에는 모든 페이지 정보와 이미지가 포함됨
    - 문서 전체에 대한 요약이 자동으로 생성됨
    """
    try:
        search_engine = request.state.search_engine

        result = search_engine.migrate_to_document_structure_in_place()

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        return {
            "success": True,
            "message": f"{result['processed_documents']}개 문서가 통합되었습니다.",
            "details": result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"문서 통합 중 오류 발생: {e}")
        raise HTTPException(status_code=500, detail=f"문서 통합 중 오류 발생: {str(e)}")


@router.delete("/document/{document_id}")
async def delete_document(request: Request, document_id: str):
    """
    문서 삭제 API
    """
    try:
        search_engine = request.state.search_engine

        if not search_engine.collection:
            raise HTTPException(status_code=500, detail="데이터베이스 연결이 설정되지 않았습니다.")

        result = search_engine.collection.delete_one({"_id": document_id})

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail=f"문서를 찾을 수 없습니다: {document_id}")

        return {
            "success": True,
            "message": f"문서 ID: {document_id}가 삭제되었습니다."
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"문서 삭제 중 오류 발생: {e}")
        raise HTTPException(status_code=500, detail=f"문서 삭제 중 오류 발생: {str(e)}")


@router.delete("/folder/{folder_name}")
async def delete_folder(request: Request, folder_name: str):
    """
    폴더 삭제 API
    """
    try:
        search_engine = request.state.search_engine

        if not search_engine.collection:
            raise HTTPException(status_code=500, detail="데이터베이스 연결이 설정되지 않았습니다.")

        result = search_engine.collection.delete_many({"folder_name": folder_name})

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail=f"폴더를 찾을 수 없습니다: {folder_name}")

        return {
            "success": True,
            "message": f"폴더: {folder_name}의 {result.deleted_count}개 문서가 삭제되었습니다."
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"폴더 삭제 중 오류 발생: {e}")
        raise HTTPException(status_code=500, detail=f"폴더 삭제 중 오류 발생: {str(e)}")