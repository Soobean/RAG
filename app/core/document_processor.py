import os
import logging
from typing import Dict, Any, List
from datetime import datetime
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocumentProcessor:
    """GPT-4o 기반 문서 처리 및 인덱싱 클래스"""

    def __init__(self, config: Dict[str, Any], search_engine):
        """
        문서 처리기 초기화
        """
        self.config = config
        self.search_engine = search_engine
        self.openai_client = search_engine.openai_client

        self.processing_config = config.get('processing', {})
        self.max_image_width = self.processing_config.get('max_image_width', 1000)
        self.image_quality = self.processing_config.get('default_compression_quality', 85)
        self.max_image_size_kb = self.processing_config.get('max_image_size_kb', 1024)
        self.multimodal_model = config.get('openai', {}).get('multimodal_model', 'gpt-4o')

        self.pdf_processor = None
        self.pptx_processor = None
        self.current_document_name = ""

    def process_document(self, file_path: str) -> Dict[str, Any]:
        """
        GPT-4o 기반 문서 처리 메인 함수

        Args:
            file_path: 처리할 문서 경로

        Returns:
            처리 결과 정보
        """
        try:
            self.current_document_name = os.path.basename(file_path).split('.')[0]
            file_extension = os.path.splitext(file_path)[1].lower()

            logger.info(f"문서 처리 시작: {self.current_document_name}{file_extension}")

            if file_extension == '.pdf':
                processed_pages = self._process_pdf(file_path)
            elif file_extension == '.pptx':
                processed_pages = self._process_pptx(file_path)
            else:
                raise ValueError(f"지원되지 않는 파일 형식: {file_extension}")

            if hasattr(self.search_engine, 'migrate_to_document_structure_in_place'):
                migrate_func = getattr(self.search_engine, 'migrate_to_document_structure_in_place')
                if callable(migrate_func):
                    try:
                        self.search_engine.migrate_to_document_structure_in_place()
                    except Exception as e:
                        logger.warning(f"문서 구조 마이그레이션 중 오류: {e}")

            return {
                "document_name": self.current_document_name,
                "pages_processed": len(processed_pages),
                "pages": processed_pages,
                "status": "success"
            }

        except Exception as e:
            logger.error(f"문서 처리 중 오류 발생: {e}", exc_info=True)
            return {
                "document_name": getattr(self, 'current_document_name', "unknown"),
                "pages_processed": 0,
                "status": "error",
                "error": str(e)
            }

    def _process_pdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        """PDF 파일 처리 - 필요할 때 동적으로 클래스 로드"""
        try:
            if self.pdf_processor is None:
                try:
                    from processors.pdf_processor import PDFProcessor
                    self.pdf_processor = PDFProcessor(self.config, self.openai_client)
                except ImportError:
                    logger.warning("PyMuPDF 임포트 실패, 내장 기본 처리기 사용")
                    self.pdf_processor = self._create_fallback_pdf_processor()

            pages_data = self.pdf_processor.process(pdf_path, self.current_document_name)
            processed_pages = []

            for page_data in pages_data:
                page_data['combined_embedding'] = self._create_optimized_embedding(page_data)
                document = self._prepare_for_storage(page_data)
                self.search_engine.upsert_document(document)

                processed_pages.append({
                    'page_number': page_data.get('page_number', ''),
                    'summary': page_data.get('page_summary', '')
                })

            return processed_pages

        except Exception as e:
            logger.error(f"PDF 처리 중 오류: {e}", exc_info=True)
            return []

    def _process_pptx(self, pptx_path: str) -> List[Dict[str, Any]]:
        """PPTX 파일 처리 - 필요할 때 동적으로 클래스 로드"""
        try:
            if self.pptx_processor is None:
                try:
                    from processors.pptx_processor import PPTXProcessor
                    self.pptx_processor = PPTXProcessor(self.config)
                except ImportError:
                    logger.warning("python-pptx 임포트 실패, 내장 기본 처리기 사용")
                    # 기본 PPTX 처리 로직 구현
                    self.pptx_processor = self._create_fallback_pptx_processor()

            pages_data = self.pptx_processor.process(pptx_path, self.current_document_name)
            processed_pages = []

            for page_data in pages_data:
                if 'images' in page_data and page_data['images']:
                    analysis_result = self._analyze_with_gpt4o(page_data['images'][0])
                    page_data['page_summary'] = analysis_result.get('page_summary', '')
                    page_data['elements'] = analysis_result.get('elements', [])

                page_data['combined_embedding'] = self._create_optimized_embedding(page_data)
                document = self._prepare_for_storage(page_data)
                self.search_engine.upsert_document(document)

                processed_pages.append({
                    'page_number': page_data.get('page_number', ''),
                    'summary': page_data.get('page_summary', '')
                })

            return processed_pages

        except Exception as e:
            logger.error(f"PPTX 처리 중 오류: {e}", exc_info=True)
            return []

    def _create_fallback_pdf_processor(self):
        """PyMuPDF 없을 때 기본 PDF 처리기 생성"""

        class BasicPDFProcessor:
            def __init__(self, config, openai_client):
                self.config = config
                self.openai_client = openai_client

            def process(self, pdf_path, folder_name):
                try:
                    import PyPDF2
                    pages_data = []

                    with open(pdf_path, 'rb') as f:
                        reader = PyPDF2.PdfReader(f)
                        for i, page in enumerate(reader.pages):
                            text = page.extract_text()
                            pages_data.append({
                                'folder_name': folder_name,
                                'page_number': str(i + 1),
                                'text_content': text,
                                'page_summary': f"페이지 {i + 1}",
                                'images': [],
                                'elements': []
                            })
                    return pages_data
                except Exception as e:
                    logger.error(f"기본 PDF 처리 중 오류: {e}")
                    return []

        return BasicPDFProcessor(self.config, self.openai_client)

    def _create_fallback_pptx_processor(self):
        """python-pptx 없을 때 기본 PPTX 처리기 생성"""

        class BasicPPTXProcessor:
            def __init__(self, config):
                self.config = config

            def process(self, pptx_path, folder_name):
                return [{
                    'folder_name': folder_name,
                    'page_number': '1',
                    'text_content': "PPTX 파일 처리 라이브러리가 설치되지 않았습니다.",
                    'page_summary': "PPTX 처리 불가",
                    'images': [],
                    'elements': []
                }]

        return BasicPPTXProcessor(self.config)

    def _analyze_with_gpt4o(self, image_data):
        """
        GPT-4o를 사용하여 이미지 분석

        Args:
            image_data: Base64 인코딩된 이미지

        Returns:
            분석 결과
        """
        if not self.openai_client:
            logger.error("OpenAI 클라이언트가 초기화되지 않았습니다.")
            return {"elements": [], "page_summary": "분석 실패: OpenAI 클라이언트 없음"}

        if not image_data or not image_data.startswith('data:image'):
            logger.error("유효하지 않은 이미지 데이터")
            return {"elements": [], "page_summary": "분석 실패: 이미지 데이터 없음"}

        try:
            messages = [
                {
                    "role": "system",
                    "content": """
                    문서 분석 전문가로서 페이지 이미지를 분석하세요. 각 요소(이미지, 텍스트)를 식별하고 
                    다음 정보를 제공하세요:

                    1. 각 이미지 요소의 대략적 위치, 유형(스크린샷, 도표, 로고 등), 내용 설명
                    2. 각 텍스트 요소의 대략적 위치, 유형(제목, 본문, 캡션 등), 내용 요약
                    3. 텍스트-이미지 간 연관 관계(예: "이 텍스트는 왼쪽 도표를 설명함")

                    JSON 형식으로 응답하세요:
                    {
                      "elements": [
                        {
                          "type": "image",
                          "coordinates": {"x1": 0, "y1": 0, "x2": 100, "y2": 100},
                          "content_type": "screenshot|chart|diagram|photo|logo",
                          "description": "이미지에 대한 간결한 설명",
                          "related_text_ids": [1, 3]
                        },
                        {
                          "type": "text",
                          "coordinates": {"x1": 0, "y1": 0, "x2": 100, "y2": 100},
                          "content_type": "title|heading|body|caption|list",
                          "summary": "텍스트 내용 요약"
                        }
                      ],
                      "page_summary": "페이지 전체 내용 요약"
                    }
                    """
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "이 문서 페이지를 분석하여 이미지와 텍스트 요소를 구분하고 상세 정보를 제공해주세요."
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": image_data}
                        }
                    ]
                }
            ]

            response = self.openai_client.chat.completions.create(
                model=self.multimodal_model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.2
            )

            result = json.loads(response.choices[0].message.content)
            logger.info(f"GPT-4o 분석 결과: {len(result.get('elements', []))}개 요소 감지")
            return result

        except Exception as e:
            logger.error(f"GPT-4o 분석 오류: {e}", exc_info=True)
            return {"elements": [], "page_summary": f"분석 실패: {str(e)}"}

    def _create_optimized_embedding(self, processed_content):
        """최적화된 임베딩 텍스트 생성"""
        embedding_text = f"""
        문서: {processed_content.get('folder_name', '')}
        페이지: {processed_content.get('page_number', '')}
        요약: {processed_content.get('page_summary', '')}

        텍스트 내용:
        {processed_content.get('text_content', '')[:4000]}

        이미지 설명:
        """

        for img in processed_content.get('images', []):
            if isinstance(img, dict):
                embedding_text += f"- {img.get('description', '')}\n"
            else:
                embedding_text += "- 이미지\n"

        return self.search_engine.generate_embedding(embedding_text)

    def _prepare_for_storage(self, processed_content):
        """저장용 문서 형식 준비"""
        document = {
            '_id': f"{processed_content['folder_name']}_page_{processed_content['page_number']}",
            'folder_name': processed_content['folder_name'],
            'page_number': processed_content['page_number'],
            'description': processed_content.get('text_content', ''),
            'page_summary': processed_content.get('page_summary', ''),
            'images': processed_content.get('images', []),
            'elements': processed_content.get('elements', []),
            'combined_embedding': processed_content['combined_embedding'],
            'created_at': datetime.now(),
            'content_type': 'processed_page'
        }

        return document