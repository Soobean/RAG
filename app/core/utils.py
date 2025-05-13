import io
import base64
from PIL import Image
import logging

logger = logging.getLogger(__name__)


def process_image(img, max_width=1000, quality=85):
    """
    이미지 처리 및 Base64 인코딩

    Args:
        img: PIL 이미지 객체
        max_width: 최대 이미지 너비
        quality: JPEG 압축 품질

    Returns:
        Base64 인코딩된 이미지 문자열
    """
    try:
        if img.width > max_width:
            ratio = max_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((max_width, new_height), Image.LANCZOS)

        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality, optimize=True)
        buffer.seek(0)

        encoded_image = base64.b64encode(buffer.read()).decode('utf-8')
        return f"data:image/jpeg;base64,{encoded_image}"
    except Exception as e:
        logger.error(f"이미지 처리 오류: {e}")
        return ""


def safe_int(value, default=0):
    """
    문자열을 안전하게 정수로 변환

    Args:
        value: 변환할 값
        default: 변환 실패 시 반환할 기본값

    Returns:
        변환된 정수 또는 기본값
    """
    if not value:
        return default

    if isinstance(value, int):
        return value

    try:
        clean_value = ''.join(c for c in str(value) if c.isdigit())
        return int(clean_value) if clean_value else default
    except:
        return default


def truncate_text(text, max_length=100, suffix="..."):
    """
    텍스트를 지정된 길이로 자르기

    Args:
        text: 원본 텍스트
        max_length: 최대 길이
        suffix: 잘린 경우 접미사

    Returns:
        잘린 텍스트
    """
    if not text:
        return ""

    if len(text) <= max_length:
        return text

    return text[:max_length] + suffix