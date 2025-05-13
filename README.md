# PDF 문서 검색 시스템

GPT-4o 기반 문서 처리 및 검색 시스템

## 개요

이 시스템은 PDF 및 PPTX 문서를 업로드하여 GPT-4o로 분석하고, 벡터 검색을 통해 문서를 검색할 수 있는 기능을 제공합니다.

## 주요 기능

- PDF 및 PPTX 파일 업로드 및 처리
- GPT-4o를 이용한 문서 이미지 분석
- 문서 텍스트 및 이미지 추출
- 벡터 검색 기반 문서 검색
- 문서 통합 및 관리

## 시스템 요구사항

- Python 3.8 이상
- 필수 패키지 (requirements.txt 참조)
- Azure OpenAI 서비스 계정
- Azure Cosmos DB for MongoDB (또는 MongoDB)

## 설치 방법

1. 저장소 복제:
   ```bash
   git clone https://github.com/your-repo/document-search-system.git
   cd document-search-system
   ```

2. 가상 환경 생성 및 활성화:
   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # Linux/Mac
   source .venv/bin/activate
   ```

3. 필수 패키지 설치:
   ```bash
   pip install -r requirements.txt
   ```

4. 환경 변수 설정:
   ```bash
   # .env 파일 생성
   cp .env.example .env
   # .env 파일을 열어 API 키와 엔드포인트 설정
   ```

## 환경 변수 설정

다음 환경 변수를 .env 파일에 설정하세요:

```
AZURE_OPENAI_ENDPOINT=https://your-azure-openai-endpoint.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
COSMOS_CONNECTION_STRING=your-cosmos-connection-string
COSMOS_DATABASE=SKEP_AIPLATFORM_LOCAL
COSMOS_COLLECTION=welfare
```

## 실행 방법

### API 서버 실행

```bash
python app/run.py --mode api --port 8000
```

서버가 시작되면 `http://localhost:8000`으로 접속할 수 있습니다.

### 문서 처리 모드

특정 문서를 처리하려면:

```bash
python app/run.py --mode process --file path/to/your/document.pdf
```

## API 엔드포인트

### 검색 API

- `POST /api/search` - 문서 검색 및 답변 생성

### 문서 관리 API

- `POST /api/upload` - 문서 업로드 및 처리
- `GET /api/list` - 문서 목록 조회
- `POST /api/consolidate` - 페이지 단위 문서를 문서 단위로 통합
- `DELETE /api/document/{document_id}` - 문서 삭제
- `DELETE /api/folder/{folder_name}` - 폴더 삭제

## 문제 해결

### PyMuPDF 설치 문제

PyMuPDF(fitz) 라이브러리 설치 중 문제가 발생할 경우:

```bash
pip install pymupdf==1.23.6 --no-cache-dir
```

### PDF 및 PPTX 처리 문제

시스템은 자동으로 필요한 라이브러리가 없는 경우 대체 처리 로직을 사용합니다:

- PyMuPDF가 없는 경우 PyPDF2로 대체
- python-pptx가 없는 경우 기본 텍스트 처리 로직 사용

### 연결 오류

MongoDB 또는 Azure OpenAI 연결 문제가 발생할 경우:

1. `.env` 파일의 설정 확인
2. 네트워크 연결 확인
3. API 키와 엔드포인트가 올바른지 확인

## 폴더 구조

```
app/
├── config/             # 설정 관련 파일
├── core/               # 핵심 기능 클래스
├── processors/         # 문서 처리 전용 클래스
├── api/                # API 관련 모듈
│   ├── models/         # API 모델 정의
│   └── routes/         # API 라우트 정의
├── static/             # 정적 파일 (CSS, JS, 이미지 등)
└── run.py              # 메인 실행 파일
```