import os
import logging
from typing import Dict, Any, List, Optional, Tuple

from processors.pdf_processor import PDFProcessor
from processors.pptx_processor import PPTXProcessor
from core.embeddings import EmbeddingManager
from core.utils import safe_int

# 로깅 설정
logger = logging.getLogger(__name__)


class DocumentProcessor:
    """문서 처리 및 인덱싱 핵심 클래스"""

    def __init__(self, config: Dict[str, Any], search_engine):
        """
        문서 처리기 초기화

        Args:
            config: 애플리케이션 설정
            search_engine: 검색 엔진 인스턴스
        """
        self.config = config
        self.search_engine = search_engine

        self.doc_intelligence_client = self._init_document_intelligence()

        self.embedding_manager = EmbeddingManager(
            search_engine.openai_client,
            config['openai'].get('embedding_model', 'text-embedding-3-small')
        )

        self.processors = self._init_processors()

    def _init_document_intelligence(self):
        """Document Intelligence 클라이언트 초기화"""
        try:
            from azure.ai.documentintelligence import DocumentIntelligenceClient
            from azure.core.credentials import AzureKeyCredential

            endpoint = self.config['document'].get('intelligence_endpoint')
            key = self.config['document'].get('intelligence_key')

            if not endpoint or not key:
                logger.warning("Document Intelligence 설정이 없습니다. 일부 기능이 제한될 수 있습니다.")
                return None

            return DocumentIntelligenceClient(
                endpoint=endpoint,
                credential=AzureKeyCredential(key)
            )
        except ImportError:
            logger.warning("azure-ai-documentintelligence 패키지가 설치되지 않았습니다.")
            return None
        except Exception as e:
            logger.error(f"Document Intelligence 클라이언트 초기화 오류: {e}")
            return None

    def _init_processors(self) -> Dict[str, Any]:
        """문서 유형별 프로세서 초기화"""
        processors = {}

        if self.doc_intelligence_client:
            processors['.pdf'] = PDFProcessor(self.config, self.doc_intelligence_client)
        else:
            logger.warning("Document Intelligence 클라이언트가 없어 PDF 처리가 제한됩니다.")

        processors['.pptx'] = PPTXProcessor(self.config)

        return processors

    def process_document(self, file_path: str) -> Dict[str, Any]:
        """
        문서 처리 및 인덱싱 메인 함수

        Args:
            file_path: 처리할 문서 경로

        Returns:
            처리 결과 정보

        Raises:
            ValueError: 지원되지 않는 파일 형식인 경우
            Exception: 문서 처리 중 오류 발생 시
        """
        try:
            file_extension = os.path.splitext(file_path)[1].lower()
            document_name = os.path.basename(file_path).split('.')[0]

            logger.info(f"문서 처리 시작: {document_name}{file_extension}")

            if file_extension not in self.processors:
                supported_formats = ', '.join(self.processors.keys())
                raise ValueError(f"지원되지 않는 파일 형식: {file_extension}. 지원 형식: {supported_formats}")

            processor = self.processors[file_extension]

            document_data = processor.process(file_path)
            if not document_data:
                raise Exception(f"문서 처리 실패: {document_name}")

            processed_count = self._index_document(document_data)

            result = {
                "document_name": document_data['document_name'],
                "pages_processed": processed_count,
                "status": "success"
            }

            logger.info(f"문서 처리 완료: {document_name}, {processed_count}페이지")
            return result

        except ValueError as e:
            logger.error(f"문서 처리 값 오류: {e}")
            raise
        except Exception as e:
            logger.error(f"문서 처리 중 오류 발생: {e}", exc_info=True)
            raise Exception(f"문서 처리 중 오류 발생: {str(e)}")

    def _index_document(self, document_data: Dict[str, Any]) -> int:
        """
        처리된 문서 데이터를 검색 엔진에 인덱싱

        Args:
            document_data: 처리된 문서 데이터

        Returns:
            처리된 페이지 수
        """
        processed_count = 0
        folder_name = document_data['document_name']
        pages = document_data.get('pages', [])

        try:
            for page_data in pages:
                try:
                    if 'folder_name' not in page_data:
                        page_data['folder_name'] = folder_name

                    if 'combined_embedding' not in page_data:
                        page_data['combined_embedding'] = self._create_optimized_embedding(page_data)

                    self.search_engine.upsert_document(self._prepare_for_storage(page_data))
                    processed_count += 1
                except Exception as e:
                    logger.error(f"페이지 처리 중 오류: {e}", exc_info=True)

            if processed_count > 0 and hasattr(self.search_engine, 'migrate_to_document_structure_in_place'):
                try:
                    self.search_engine.migrate_to_document_structure_in_place()
                except Exception as e:
                    logger.warning(f"문서 구조 마이그레이션 중 오류: {e}")

            return processed_count

        except Exception as e:
            logger.error(f"문서 인덱싱 중 오류: {e}", exc_info=True)
            return processed_count

    def _create_optimized_embedding(self, page_data: Dict[str, Any]) -> List[float]:
        """
        페이지 콘텐츠에 최적화된 임베딩 생성

        Args:
            page_data: 페이지 데이터

        Returns:
            임베딩 벡터
        """
        folder_name = page_data.get('folder_name', '')
        page_number = page_data.get('page_number', '')
        description = page_data.get('description', '')

        key_information = ""
        chat_relevance = ""
        image_description = ""

        try:
            content_analysis = page_data.get('content_analysis', '{}')
            if isinstance(content_analysis, str):
                import json
                try:
                    analysis = json.loads(content_analysis)
                    key_information = analysis.get('key_information', '')
                    chat_relevance = analysis.get('chat_relevance', '')
                    image_description = analysis.get('image_description', '')
                except json.JSONDecodeError:
                    logger.warning(f"콘텐츠 분석 JSON 파싱 오류: {content_analysis[:100]}...")
            elif isinstance(content_analysis, dict):
                key_information = content_analysis.get('key_information', '')
                chat_relevance = content_analysis.get('chat_relevance', '')
                image_description = content_analysis.get('image_description', '')
        except Exception as e:
            logger.warning(f"콘텐츠 분석 처리 중 오류: {e}")

        embedding_text = f"""
        문서: {folder_name}
        페이지: {page_number}
        내용: {description[:3000] if description else ''}
        핵심 정보: {key_information}
        관련 질문: {chat_relevance}
        이미지 설명: {image_description}
        """

        return self.embedding_manager.generate_embedding(embedding_text)

    def _prepare_for_storage(self, page_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        검색 엔진 저장을 위한 문서 형식 준비

        Args:
            page_data: 페이지 데이터

        Returns:
            저장용 문서 데이터
        """
        document = {
            'folder_name': page_data.get('folder_name', ''),
            'page_number': page_data.get('page_number', ''),
            'description': page_data.get('description', ''),
            'combined_embedding': page_data.get('combined_embedding', [])
        }

        if 'images' in page_data and isinstance(page_data['images'], list):
            document['images'] = page_data['images']

        if 'layout_info' in page_data:
            try:
                import json
                if isinstance(page_data['layout_info'], dict):
                    document['layout_metadata'] = json.dumps(page_data['layout_info'])
                elif isinstance(page_data['layout_info'], str):
                    document['layout_metadata'] = page_data['layout_info']
            except Exception as e:
                logger.warning(f"레이아웃 메타데이터 처리 중 오류: {e}")

        if 'content_analysis' in page_data:
            document['content_analysis'] = page_data['content_analysis']

        if 'key_information' in page_data:
            document['key_information'] = page_data['key_information']

        return document

    def analyze_content(self, text: str, image_data: Optional[str] = None) -> Dict[str, Any]:
        """
        텍스트와 이미지 콘텐츠 분석 (선택적 기능)

        Args:
            text: 분석할 텍스트
            image_data: 이미지 데이터 (선택 사항)

        Returns:
            분석 결과
        """
        try:
            if not self.search_engine.openai_client:
                logger.warning("OpenAI 클라이언트가 없어 콘텐츠 분석이 불가능합니다.")
                return {"error": "분석 서비스를 사용할 수 없습니다."}

            multimodal_model = self.config['openai'].get('multimodal_model', 'gpt-4o')

            messages = [
                {
                    "role": "system",
                    "content": "페이지 콘텐츠 분석 전문가입니다. 텍스트와 이미지를 분석하여 정확한 정보를 제공합니다."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"""
                            다음 콘텐츠를 분석해주세요:

                            텍스트 내용: {text[:1000] if text else '(텍스트 없음)'}

                            다음 정보를 JSON 형식으로 제공해주세요:
                            1. content_type: 이 콘텐츠의 주요 유형 (설명서, 가이드, 테이블 등)
                            2. key_information: 이 콘텐츠의 핵심 정보 (50자 이내)
                            3. chat_relevance: 챗봇 대화 시 이 콘텐츠가 어떤 질문에 관련이 있을지
                            """
                        }
                    ]
                }
            ]

            if image_data and image_data.startswith('data:image'):
                messages[1]["content"].append({
                    "type": "image_url",
                    "image_url": {"url": image_data}
                })

                messages[1]["content"][0]["text"] += "\n4. image_description: 이미지가 어떤 내용을 보여주는지 설명"

            response = self.search_engine.openai_client.chat.completions.create(
                model=multimodal_model,
                messages=messages,
                temperature=0.3,
                response_format={"type": "json_object"}
            )

            result = response.choices[0].message.content

            import json
            return json.loads(result)

        except Exception as e:
            logger.error(f"콘텐츠 분석 중 오류: {e}", exc_info=True)
            return {
                "content_type": "알 수 없음",
                "key_information": "분석 실패",
                "chat_relevance": "문서 관련 질문",
                "image_description": "알 수 없음"
            }