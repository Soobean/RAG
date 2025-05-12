# 통합 문서 검색 시스템

이 프로젝트는 PDF 및 PPTX 문서를 업로드하고, 이를 분석하여 자연어 질의응답이 가능한 통합 문서 검색 시스템입니다. Azure OpenAI, Azure Document Intelligence, Azure Cosmos DB를 활용하여 고성능 의미 검색과 답변 생성 기능을 제공합니다.

## 주요 기능

- **다양한 문서 형식 지원**: PDF, PPTX 파일 처리
- **문서 레이아웃 분석**: Azure Document Intelligence를 활용한 자동 레이아웃 분석
- **벡터 임베딩 검색**: 의미 기반 유사도 검색으로 관련 정보 빠르게 검색
- **자연어 질의응답**: 질문에 대한 정확한 답변 생성
- **이미지 및 텍스트 추출**: 문서 내 이미지와 텍스트 정보 통합 처리
- **사용자 친화적 인터페이스**: 직관적인 웹 인터페이스 제공

## 시스템 아키텍처

```
┌───────────────────────────────────────────────────────┐
│                      API 서버                          │
│                                                       │
│  ┌────────────┐      ┌────────────┐      ┌─────────┐  │
│  │ 문서 처리    │      │ 검색 엔진    │      │ 응답     │   │
│  │ 컴포넌트     │<────>│ 컴포넌트     │<────>│ 생성기    │  │ 
│  └────────────┘      └────────────┘      └─────────┘  │
│         ▲                  ▲                  ▲       │
└─────────┼──────────────────┼──────────────────┼───────┘
          │                  │                  │
          ▼                  ▼                  ▼
┌───────────────┐    ┌──────────────────┐    ┌─────────────┐
│ Azure Document│    │  Azure Cosmos DB │    │ Azure OpenAI│
│ Intelligence  │    │  (MongoDB)       │    │ 서비스        │
└───────────────┘    └──────────────────┘    └─────────────┘
```

## 기술 스택

- **백엔드**: Python, FastAPI
- **프론트엔드**: HTML, CSS, JavaScript
- **데이터베이스**: Azure Cosmos DB for MongoDB
- **AI 서비스**:
  - Azure OpenAI (GPT-4, Embeddings)
  - Azure Document Intelligence
- **문서 처리**:
  - PyMuPDF (PDF 처리)
  - python-pptx (PPTX 처리)

## 설치 방법

### 사전 요구사항

- Python 3.8 이상
- Azure 구독 및 관련 서비스 설정:
  - Azure OpenAI
  - Azure Cosmos DB for MongoDB
  - Azure Document Intelligence

### 설치 단계

1. 저장소 복제
   ```bash
   git clone https://github.com/soobean/RAG.git
   cd document-search-system
   ```

2. 가상 환경 설정 및 패키지 설치
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. 환경 변수 설정
   ```bash
   # .env 파일 생성
   cp .env.example .env
   # .env 파일을 편집하여 API 키 및 엔드포인트 설정
   ```

4. 애플리케이션 실행
   ```bash
   python run.py
   ```

## 환경 변수 설정

`.env` 파일에 다음 변수들을 설정해야 합니다:

```
# Azure OpenAI 설정
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key

# Azure Document Intelligence 설정
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://your-resource-name.cognitiveservices.azure.com/
AZURE_DOCUMENT_INTELLIGENCE_KEY=your-key

# Azure Cosmos DB 설정
COSMOS_CONNECTION_STRING=your-connection-string
COSMOS_DATABASE=your-database-name
COSMOS_COLLECTION=your-collection-name
```

## 사용 방법

### 문서 업로드

1. 웹 인터페이스 접속 (기본 URL: http://localhost:8000)
2. "문서 업로드" 버튼을 클릭하여 PDF 또는 PPTX 파일 선택
3. 업로드 완료 후 처리 상태 확인

### 질의응답

1. 검색창에 질문 입력
2. "답변 생성" 버튼 클릭
3. 관련 답변과 참조 문서, 이미지 확인

## API 문서

API 문서는 Swagger UI를 통해 접근할 수 있습니다: http://localhost:8000/docs

### 주요 API 엔드포인트

- **POST /api/documents/upload**: 문서 업로드 및 처리
- **POST /api/search/query**: 질의응답 검색
- **GET /api/documents/list**: 처리된 문서 목록 조회

## 프로젝트 구조

```
document_search_system/
│
├── config/                   # 설정 파일
│   ├── config.json           # 애플리케이션 설정
│   └── env_loader.py         # 환경 변수 로더
│
├── core/                     # 핵심 모듈
│   ├── search_engine.py      # 검색 엔진
│   ├── document_processor.py # 문서 처리 클래스
│   ├── embeddings.py         # 임베딩 생성
│   └── utils.py              # 유틸리티 함수
│
├── processors/               # 문서 처리기
│   ├── pdf_processor.py      # PDF 처리
│   └── pptx_processor.py     # PPTX 처리
│
├── api/                      # API 서버
│   ├── main.py               # FastAPI 서버
│   ├── routes/               # API 라우트
│   └── models/               # 데이터 모델
│
├── static/                   # 정적 파일
│   ├── css/                  # 스타일시트
│   ├── js/                   # 자바스크립트
│   └── index.html            # 메인 페이지
│
├── scripts/                  # 유틸리티 스크립트
├── .env.example              # 환경 변수 예시
├── requirements.txt          # 의존성 목록
├── README.md                 # 이 파일
└── run.py                    # 애플리케이션 실행 스크립트
```

## 개발자 안내

### 추가 기능 개발

문서 유형 추가:
1. `processors/` 디렉토리에 새 프로세서 클래스 추가
2. `core/document_processor.py`에 새 프로세서 등록

검색 방식 확장:
1. `core/search_engine.py`에 새 검색 메서드 추가
2. `api/routes/search.py`에 새 API 엔드포인트 추가


## 성능 최적화 포인트

- **임베딩 최적화**: 문서 핵심 정보 우선 처리로 검색 정확도 향상
- **이미지 최적화**: 최대 너비 및 품질 제한으로 저장 공간 효율화
- **검색 속도**: 최적화된 쿼리 파이프라인으로 검색 성능 향상
- **응답 생성**: 관련성 높은 컨텍스트만 활용하여 토큰 사용 최소화


## 문의 및 기여

이슈나 기능 제안은 GitHub 이슈 트래커를 통해 제출해주세요.
