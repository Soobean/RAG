import os
import tempfile
import subprocess
from PIL import Image, ImageDraw, ImageFont
import io
import base64
from core.utils import process_image, safe_int


class PPTXProcessor:
    """PPTX 파일 처리 클래스"""

    def __init__(self, config):
        """
        PPTX 처리기 초기화
        :param config: 애플리케이션 설정
        """
        self.max_image_width = config['processing'].get('max_image_width', 1000)
        self.image_quality = config['processing'].get('default_compression_quality', 85)

    def process(self, pptx_path):
        """
        PPTX 처리 메인 함수
        :param pptx_path: PPTX 파일 경로
        :return: 처리된 문서 데이터
        """
        folder_name = os.path.basename(pptx_path).split('.')[0]

        try:
            from pptx import Presentation
            prs = Presentation(pptx_path)

            pages_data = []
            for slide_idx, slide in enumerate(prs.slides):
                slide_num = slide_idx + 1

                slide_text = self._extract_slide_text(slide)

                slide_image = self._extract_slide_as_image(slide, pptx_path, slide_idx)

                slide_data = {
                    "folder_name": folder_name,
                    "page_number": str(slide_num),
                    "description": slide_text,
                    "images": [slide_image],
                    "layout_info": {
                        "page_structure": "slide_content",
                        "text_regions": [{"content": slide_text}] if slide_text else [],
                        "image_regions": [{"region": "full"}]
                    }
                }

                pages_data.append(slide_data)

            return {
                "document_name": folder_name,
                "pages": pages_data
            }

        except ImportError:
            return self._process_pptx_alternative(pptx_path, folder_name)

    def _extract_slide_text(self, slide):
        """
        슬라이드에서 텍스트 추출
        :param slide: pptx 슬라이드 객체
        :return: 추출된 텍스트
        """
        slide_text = ""

        for shape in slide.shapes:
            if hasattr(shape, "text") and shape.text.strip():
                slide_text += shape.text + "\n"

        return slide_text.strip()

    def _extract_slide_as_image(self, slide, pptx_path, slide_idx):
        """
        슬라이드를 이미지로 변환
        :param slide: pptx 슬라이드 객체
        :param pptx_path: PPTX 파일 경로
        :param slide_idx: 슬라이드 인덱스
        :return: 이미지 데이터 (Base64)
        """
        try:
            return self._extract_via_libreoffice(pptx_path, slide_idx)
        except Exception as e:
            print(f"LibreOffice 변환 실패: {e}")
            try:
                return self._create_text_image(slide, slide_idx)
            except Exception as e:
                print(f"텍스트 이미지 생성 실패: {e}")
                return self._create_default_image(slide_idx)

    def _extract_via_libreoffice(self, pptx_path, slide_idx):
        """
        LibreOffice를 사용해 슬라이드 추출
        :param pptx_path: PPTX 파일 경로
        :param slide_idx: 슬라이드 인덱스
        :return: 이미지 데이터 (Base64)
        """
        temp_dir = tempfile.mkdtemp()
        output_pdf = os.path.join(temp_dir, "slides.pdf")

        subprocess.call([
            'soffice',
            '--headless',
            '--convert-to', 'pdf',
            '--outdir', temp_dir,
            pptx_path
        ])

        import fitz
        doc = fitz.open(output_pdf)
        if slide_idx < len(doc):
            page = doc[slide_idx]
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            doc.close()

            import shutil
            shutil.rmtree(temp_dir)

            return process_image(img, self.max_image_width, self.image_quality)

        raise Exception("슬라이드를 찾을 수 없습니다")

    def _create_text_image(self, slide, slide_idx):
        """
        슬라이드 텍스트 기반 이미지 생성
        :param slide: pptx 슬라이드 객체
        :param slide_idx: 슬라이드 인덱스
        :return: 이미지 데이터 (Base64)
        """
        width, height = 1024, 768
        img = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(img)

        font = ImageFont.load_default()

        draw.text((20, 20), f"슬라이드 {slide_idx + 1}", fill='black', font=font)

        text = ""
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                text += shape.text + "\n"

        y_position = 60
        for line in text.split('\n'):
            draw.text((20, y_position), line, fill='black', font=font)
            y_position += 20
            if y_position > height - 40:
                break

        return process_image(img, self.max_image_width, self.image_quality)

    def _create_default_image(self, slide_idx):
        """
        기본 슬라이드 이미지 생성
        :param slide_idx: 슬라이드 인덱스
        :return: 이미지 데이터 (Base64)
        """
        width, height = 1024, 768
        img = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(img)

        font = ImageFont.load_default()

        draw.text((width // 2 - 100, height // 2 - 20), f"슬라이드 {slide_idx + 1}", fill='black', font=font)
        draw.text((width // 2 - 150, height // 2 + 20), "이미지를 생성할 수 없습니다", fill='black', font=font)

        return process_image(img, self.max_image_width, self.image_quality)

    def _process_pptx_alternative(self, pptx_path, folder_name):
        """
        대체 PPTX 처리 방법
        :param pptx_path: PPTX 파일 경로
        :param folder_name: 문서 폴더명
        :return: 처리된 문서 데이터
        """
        pages_data = []

        for slide_idx in range(5):
            slide_image = self._create_default_image(slide_idx)

            slide_data = {
                "folder_name": folder_name,
                "page_number": str(slide_idx + 1),
                "description": f"슬라이드 {slide_idx + 1} - 텍스트 추출 불가",
                "images": [slide_image],
                "layout_info": {
                    "page_structure": "slide_content",
                    "text_regions": [],
                    "image_regions": [{"region": "full"}]
                }
            }

            pages_data.append(slide_data)

        return {
            "document_name": folder_name,
            "pages": pages_data
        }