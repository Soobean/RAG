import os
import logging
import json
import io
import base64
from typing import Dict, Any, List
from PIL import Image

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PDFProcessor:
    """PDF 문서 처리 전용 클래스"""

    def __init__(self, config, openai_client):
        """
        PDF 처리기 초기화
        """
        self.config = config
        self.openai_client = openai_client

        # 설정 로드
        processing_config = config.get('processing', {})
        self.max_image_width = processing_config.get('max_image_width', 1000)
        self.image_quality = processing_config.get('default_compression_quality', 85)
        self.multimodal_model = config.get('openai', {}).get('multimodal_model', 'gpt-4o')

    def process(self, pdf_path, folder_name):
        """
        PDF 파일 처리
        """
        import fitz  # PyMuPDF

        doc = fitz.open(pdf_path)
        pages_data = []

        total_pages = len(doc)
        logger.info(f"PDF 처리 시작: {pdf_path}, 총 {total_pages}페이지")

        for page_idx in range(total_pages):
            page_num = page_idx + 1
            logger.info(f"페이지 {page_num}/{total_pages} 처리 중...")

            try:
                page = doc[page_idx]

                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                page_image = self._process_and_encode_image(img)

                analysis_result = self._analyze_with_gpt4o(page_image)

                page_data = self._process_page_content(page, analysis_result, folder_name, page_num)

                pages_data.append(page_data)
                logger.info(f"페이지 {page_num} 처리 완료")

            except Exception as e:
                logger.error(f"페이지 {page_num} 처리 중 오류: {e}")
                pages_data.append({
                    'folder_name': folder_name,
                    'page_number': str(page_num),
                    'text_content': f"페이지 {page_num} 처리 오류: {str(e)}",
                    'page_summary': f"페이지 {page_num} 처리 실패",
                    'images': [],
                    'elements': []
                })

        return pages_data

    def _process_and_encode_image(self, img):
        """이미지 처리 및 Base64 인코딩"""
        try:
            if img.width > self.max_image_width:
                ratio = self.max_image_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((self.max_image_width, new_height), Image.LANCZOS)

            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=self.image_quality, optimize=True)
            buffer.seek(0)

            encoded_image = base64.b64encode(buffer.read()).decode('utf-8')
            return f"data:image/jpeg;base64,{encoded_image}"
        except Exception as e:
            logger.error(f"이미지 처리 오류: {e}")
            return ""

    def _analyze_with_gpt4o(self, image_data):
        """GPT-4o를 사용하여 이미지 분석"""
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
            logger.error(f"GPT-4o 분석 오류: {e}")
            return {"elements": [], "page_summary": f"분석 실패: {str(e)}"}

    def _process_page_content(self, page, analysis_result, folder_name, page_number):
        """
        페이지 콘텐츠 처리
        """
        import fitz  # PyMuPDF

        width, height = page.rect.width, page.rect.height

        processed_content = {
            'folder_name': folder_name,
            'page_number': str(page_number),
            'page_summary': analysis_result.get('page_summary', ''),
            'text_content': '',
            'images': [],
            'elements': []
        }

        # 텍스트 추출
        processed_content['text_content'] = page.get_text("text")

        # 요소 처리
        for idx, element in enumerate(analysis_result.get('elements', [])):
            element_type = element.get('type')
            coords = element.get('coordinates', {})

            # 좌표 변환
            rect = fitz.Rect(
                coords.get('x1', 0) * width / 100,
                coords.get('y1', 0) * height / 100,
                coords.get('x2', 100) * width / 100,
                coords.get('y2', 100) * height / 100
            )

            element_data = {
                'id': idx,
                'type': element_type,
                'content_type': element.get('content_type', ''),
                'coordinates': coords
            }

            if element_type == 'image':
                try:
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=rect)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    image_data = self._process_and_encode_image(img)

                    image_info = {
                        'image': image_data,
                        'description': element.get('description', ''),
                        'related_text_ids': element.get('related_text_ids', [])
                    }

                    processed_content['images'].append(image_info)
                    element_data['description'] = element.get('description', '')
                    element_data['image_index'] = len(processed_content['images']) - 1
                except Exception as e:
                    logger.warning(f"이미지 요소 추출 오류: {e}")

            elif element_type == 'text':
                try:
                    text_content = page.get_text("text", clip=rect)

                    if text_content.strip():
                        element_data['content'] = text_content
                        element_data['summary'] = element.get('summary', '')
                        element_data['related_image_ids'] = element.get('related_image_ids', [])
                except Exception as e:
                    logger.warning(f"텍스트 요소 추출 오류: {e}")

            processed_content['elements'].append(element_data)

        if not processed_content['images']:
            try:
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                page_image = self._process_and_encode_image(img)

                processed_content['images'].append({
                    'image': page_image,
                    'description': '페이지 전체 이미지',
                    'related_text_ids': []
                })
            except Exception as e:
                logger.warning(f"전체 페이지 이미지 추출 오류: {e}")

        if not processed_content['text_content'].strip():
            processed_content['text_content'] = "텍스트 내용 없음"

        return processed_content