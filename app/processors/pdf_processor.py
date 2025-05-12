import fitz  # PyMuPDF
import os
from PIL import Image
import io
import base64
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest


class PDFProcessor:
    """PDF 문서 처리 전용 클래스"""

    def __init__(self, config, doc_intelligence_client):
        self.doc_intelligence_client = doc_intelligence_client
        self.layout_model = config['document'].get('layout_model', 'prebuilt-layout')
        self.max_image_width = config['processing'].get('max_image_width', 1000)
        self.image_quality = config['processing'].get('default_compression_quality', 85)

    def process(self, pdf_path):
        """PDF 처리 메인 함수"""
        folder_name = os.path.basename(pdf_path).split('.')[0]

        layout_result = self._analyze_layout(pdf_path)

        doc = fitz.open(pdf_path)
        pages_data = []

        for page_idx in range(len(doc)):
            page = doc[page_idx]
            page_num = page_idx + 1

            page_layout = self._extract_page_layout(layout_result, page_idx)

            page_data = self._extract_page_content(page, page_layout, folder_name, page_num)
            pages_data.append(page_data)

        return {
            "document_name": folder_name,
            "pages": pages_data
        }

    def _analyze_layout(self, pdf_path):
        """Document Intelligence 활용한 레이아웃 분석"""
        with open(pdf_path, "rb") as f:
            pdf_content = f.read()

        poller = self.doc_intelligence_client.begin_analyze_document(
            self.layout_model,
            analyze_request=AnalyzeDocumentRequest(content=pdf_content)
        )

        return poller.result()

    def _extract_page_layout(self, layout_result, page_idx):
        """페이지 레이아웃 정보 추출"""
        page_info = None
        for page in layout_result.pages:
            if page.page_number == page_idx + 1:
                page_info = page
                break

        if not page_info:
            return {"status": "not_found", "page_structure": "unknown"}

        layout = {
            "page_structure": "mixed_content",
            "text_regions": [],
            "image_regions": [],
            "table_regions": []
        }

        if hasattr(page_info, 'lines'):
            for line in page_info.lines:
                if hasattr(line, 'content') and line.content.strip():
                    layout["text_regions"].append({
                        "content": line.content
                    })

        if hasattr(layout_result, 'tables'):
            for table in layout_result.tables:
                if hasattr(table, 'bounding_regions'):
                    for region in table.bounding_regions:
                        if region.page_number == page_idx + 1:
                            layout["table_regions"].append({
                                "rows": table.row_count if hasattr(table, 'row_count') else 0,
                                "columns": table.column_count if hasattr(table, 'column_count') else 0
                            })

        return layout

    def _extract_page_content(self, page, layout, folder_name, page_num):
        """페이지 콘텐츠 추출"""
        text_content = page.get_text("text")

        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        page_image = self._process_and_encode_image(img)

        return {
            "folder_name": folder_name,
            "page_number": str(page_num),
            "description": text_content,
            "images": [page_image],
            "layout_info": layout
        }

    def _process_and_encode_image(self, img):
        """이미지 처리 및 Base64 인코딩"""
        if img.width > self.max_image_width:
            ratio = self.max_image_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((self.max_image_width, new_height), Image.LANCZOS)

        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=self.image_quality, optimize=True)
        buffer.seek(0)

        base64_image = base64.b64encode(buffer.read()).decode('utf-8')
        return f"data:image/jpeg;base64,{base64_image}"