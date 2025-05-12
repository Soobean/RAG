import os
import re
import io
import base64
from PIL import Image


def safe_int(value, default=0):
    """
    안전하게 정수로 변환
    :param value: 변환할 값
    :param default: 변환 실패 시 기본값
    :return: 정수 값
    """
    if value is None:
        return default

    if isinstance(value, int):
        return value

    try:
        if isinstance(value, str):
            clean_value = ''.join(c for c in value if c.isdigit())
            if clean_value:
                return int(clean_value)
        return default
    except:
        return default


def sanitize_filename(filename):
    """
    파일명 정리
    :param filename: 원본 파일명
    :return: 정리된 파일명
    """
    sanitized = re.sub(r'[\\/*?:"<>|]', "", filename)
    sanitized = re.sub(r'\s+', "_", sanitized)
    return sanitized


def process_image(image, max_width=1000, quality=85, max_size_kb=1024):
    """
    이미지 처리 및 최적화
    :param image: PIL Image 객체
    :param max_width: 최대 너비
    :param quality: JPEG 품질
    :param max_size_kb: 최대 파일 크기(KB)
    :return: Base64로 인코딩된 이미지
    """
    if image.width > max_width:
        ratio = max_width / image.width
        new_height = int(image.height * ratio)
        image = image.resize((max_width, new_height), Image.LANCZOS)

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=quality, optimize=True)

    if buffer.tell() > max_size_kb * 1024:
        for lower_quality in [70, 50, 30]:
            buffer.seek(0)
            buffer.truncate(0)
            image.save(buffer, format="JPEG", quality=lower_quality, optimize=True)
            if buffer.tell() <= max_size_kb * 1024:
                break

    buffer.seek(0)
    base64_encoded = base64.b64encode(buffer.read()).decode('utf-8')
    return f"data:image/jpeg;base64,{base64_encoded}"


def extract_text_from_region(text, region_type):
    """
    텍스트에서 특정 유형의 정보 추출
    :param text: 원문 텍스트
    :param region_type: 추출할 정보 유형 (title, table, paragraph 등)
    :return: 추출된 텍스트
    """
    if region_type == "title":
        lines = text.split("\n")
        return lines[0] if lines else ""

    elif region_type == "table":
        table_rows = []
        for line in text.split("\n"):
            if "|" in line or "\t" in line:
                table_rows.append(line)
        return "\n".join(table_rows)

    return text