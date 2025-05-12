import os
import tempfile
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form

router = APIRouter(
    prefix="/documents",
    tags=["documents"],
    responses={404: {"description": "Not found"}},
)


@router.post("/upload")
async def upload_document(request: Request, file: UploadFile = File(...)):
    """
    문서 업로드 및 처리 API
    """
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in ['.pdf', '.pptx']:
        raise HTTPException(status_code=400, detail="지원되지 않는 파일 형식. PDF 또는 PPTX 파일만 가능합니다.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
        temp_file.write(await file.read())
        temp_file_path = temp_file.name

    try:
        document_processor = request.state.document_processor
        result = document_processor.process_document(temp_file_path)

        return {
            "success": True,
            "message": f"{result['pages_processed']}개 페이지가 처리되었습니다.",
            "document_name": result["document_name"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"문서 처리 중 오류 발생: {str(e)}")
    finally:
        os.unlink(temp_file_path)


@router.get("/list")
async def list_documents(request: Request):
    """
    처리된 문서 목록 조회 API
    """
    try:
        search_engine = request.state.search_engine

        filter_query = {"is_consolidated": True}
        consolidated_docs = search_engine.find_document(filter_query)

        filter_query = {"is_consolidated": {"$ne": True}}
        regular_docs = search_engine.find_document(filter_query)

        document_groups = {}

        for doc in consolidated_docs:
            folder_name = doc.get("folder_name", "")
            if folder_name:
                document_groups[folder_name] = {
                    "folder_name": folder_name,
                    "type": "consolidated",
                    "pages": len(doc.get("pages", [])),
                    "created_at": doc.get("created_at", "")
                }

        for doc in regular_docs:
            folder_name = doc.get("folder_name", "")
            if folder_name and folder_name not in document_groups:
                document_groups[folder_name] = {
                    "folder_name": folder_name,
                    "type": "regular",
                    "pages": 1,
                    "created_at": doc.get("created_at", "")
                }
            elif folder_name in document_groups and document_groups[folder_name]["type"] == "regular":
                document_groups[folder_name]["pages"] += 1

        documents_list = list(document_groups.values())
        documents_list.sort(key=lambda x: x.get("folder_name", ""))

        return {"documents": documents_list, "total": len(documents_list)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"문서 목록 조회 중 오류 발생: {str(e)}")