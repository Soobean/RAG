// UI 관련 기능

// DOM 요소
const searchBtn = document.getElementById('search-btn');
const loading = document.querySelector('.loading');
const errorMessage = document.getElementById('error-message');
const answerSection = document.getElementById('answer-section');
const mainAnswer = document.getElementById('main-answer');
const sourceDocuments = document.getElementById('source-documents');
const modal = document.getElementById('imageModal');
const modalImg = document.getElementById('modalImage');
const closeBtn = document.querySelector('.close');

// 이벤트 리스너 등록
document.addEventListener('DOMContentLoaded', function() {
    // 페이지 로드 시 검색창에 포커스
    document.getElementById('query').focus();

    // 검색 버튼 이벤트
    searchBtn?.addEventListener('click', async () => {
        const query = document.getElementById('query').value.trim();
        const maxDocuments = document.getElementById('max-documents').value;

        if (!query) {
            showError('질문을 입력해주세요.');
            return;
        }

        const data = await performSearch(query, maxDocuments);
        if (data) {
            displayAnswer(data);
        }
    });

    // 모달 닫기 이벤트
    closeBtn?.addEventListener('click', function() {
        modal.style.display = "none";
    });

    // 모달 외부 클릭 시 닫기
    window.addEventListener('click', function(event) {
        if (event.target == modal) {
            modal.style.display = "none";
        }
    });
});

// 답변 표시 함수
function displayAnswer(data) {
    if (data.answer) {
        // 메인 답변 영역 초기화
        mainAnswer.innerHTML = '';

        // 답변을 문단별로 분리
        const paragraphs = data.answer.split('\n\n');

        // 각 문단 처리
        paragraphs.forEach(paragraph => {
            if (paragraph.trim() === '') return;

            // 텍스트 문단 추가
            const textPara = document.createElement('p');
            textPara.innerHTML = formatText(paragraph);
            mainAnswer.appendChild(textPara);
        });

        // 소스 문서 정보 표시
        sourceDocuments.innerHTML = '';
        if (data.source_documents && data.source_documents.length > 0) {
            data.source_documents.forEach((doc, index) => {
                const docElement = document.createElement('div');
                docElement.className = 'source-document';

                const header = document.createElement('div');
                header.className = 'document-header';

                const docName = document.createElement('div');
                docName.className = 'document-name';
                docName.textContent = `${doc.folder_name || '문서 ' + (index + 1)}`;

                header.appendChild(docName);

                // 유사도 표시
                if (doc.similarity) {
                    const similarity = document.createElement('span');
                    similarity.className = 'document-similarity';
                    similarity.textContent = `유사도: ${doc.similarity.toFixed(4)}`;
                    header.appendChild(similarity);
                }

                docElement.appendChild(header);

                // 핵심 정보 표시
                if (doc.key_information) {
                    const keyInfo = document.createElement('div');
                    keyInfo.className = 'key-info';
                    keyInfo.textContent = `핵심 정보: ${doc.key_information}`;
                    docElement.appendChild(keyInfo);
                }

                // 이미지 갤러리 추가
                if (data.images && data.images.length > 0) {
                    // 각 문서에 균등하게 이미지 배분
                    const imagesPerDoc = Math.ceil(data.images.length / data.source_documents.length);
                    const startIdx = index * imagesPerDoc;
                    const endIdx = Math.min(startIdx + imagesPerDoc, data.images.length);
                    const docImages = data.images.slice(startIdx, endIdx);

                    if (docImages.length > 0) {
                        const imagesContainer = document.createElement('div');
                        imagesContainer.className = 'gallery-grid';

                        docImages.forEach((imageData) => {
                            try {
                                // 이미지 요소 생성
                                const imageContainer = document.createElement('div');
                                imageContainer.className = 'gallery-item';

                                const img = document.createElement('img');
                                img.src = imageData;
                                img.alt = `${doc.folder_name || '문서'} 이미지`;

                                // 이미지 클릭 이벤트 - 모달로 확대
                                img.onclick = function() {
                                    modal.style.display = "block";
                                    modalImg.src = this.src;
                                };

                                // 이미지 로드 오류 처리
                                img.onerror = function() {
                                    this.onerror = null;
                                    this.src = 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMDAiIGhlaWdodD0iMTAwIiB2aWV3Qm94PSIwIDAgMTAwIDEwMCI+PHJlY3Qgd2lkdGg9IjEwMCIgaGVpZ2h0PSIxMDAiIGZpbGw9IiNlZWUiLz48dGV4dCB4PSI1MCIgeT0iNTAiIGZvbnQtc2l6ZT0iMTQiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZpbGw9IiNhYWEiPuydtOuvuOyngOy2nCDsmqnslrTshJwg7JWI64WV64uI64ukPC90ZXh0Pjwvc3ZnPg==';
                                };

                                imageContainer.appendChild(img);
                                imagesContainer.appendChild(imageContainer);
                            } catch (e) {
                                console.error('이미지 처리 중 오류:', e);
                            }
                        });

                        docElement.appendChild(imagesContainer);
                    }
                }

                sourceDocuments.appendChild(docElement);
            });
        } else {
            sourceDocuments.innerHTML = '<div class="no-results">참조 문서 정보가 없습니다.</div>';
        }

        // 답변 섹션 표시
        showAnswerSection();
    } else {
        // 결과가 없는 경우
        mainAnswer.innerHTML = '<div class="no-results">관련 답변을 찾을 수 없습니다.</div>';
        sourceDocuments.innerHTML = '';
        showAnswerSection();
    }
}

// 로딩 표시 함수
function showLoading(isLoading) {
    loading.style.display = isLoading ? 'block' : 'none';
}

// 오류 메시지 표시 함수
function showError(message) {
    errorMessage.textContent = message;
    errorMessage.style.display = 'block';
}

// 오류 메시지 숨기기 함수
function hideError() {
    errorMessage.style.display = 'none';
}

// 답변 섹션 표시 함수
function showAnswerSection() {
    answerSection.style.display = 'block';
}

// 답변 섹션 숨기기 함수
function hideAnswerSection() {
    answerSection.style.display = 'none';
}