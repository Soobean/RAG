/**
 * 검색 관련 기능 JavaScript
 */

// API 기본 URL
const API_BASE_URL = window.location.origin;

// DOM 요소
let searchBtn;
let queryInput;
let maxDocumentsInput;
let includeImagesCheckbox;
let loading;
let errorMessage;
let answerSection;
let mainAnswer;
let sourceDocuments;
let imageModal;
let modalImage;
let modalCaption;

// 초기화 함수
function initSearchUI() {
    // DOM 요소 참조
    searchBtn = document.getElementById('search-btn');
    queryInput = document.getElementById('query');
    maxDocumentsInput = document.getElementById('max-documents');
    includeImagesCheckbox = document.getElementById('include-images');
    loading = document.getElementById('loading');
    errorMessage = document.getElementById('error-message');
    answerSection = document.getElementById('answer-section');
    mainAnswer = document.getElementById('main-answer');
    sourceDocuments = document.getElementById('source-documents');
    imageModal = document.getElementById('imageModal');
    modalImage = document.getElementById('modalImage');
    modalCaption = document.getElementById('modalCaption');

    // 검색 버튼 클릭 이벤트
    searchBtn.addEventListener('click', performSearch);

    // 엔터 키 이벤트
    queryInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            performSearch();
        }
    });

    // 모달 닫기 이벤트
    document.querySelector('#imageModal .close').addEventListener('click', function() {
        imageModal.style.display = 'none';
    });

    // 모달 외부 클릭 시 닫기
    window.addEventListener('click', function(event) {
        if (event.target === imageModal) {
            imageModal.style.display = 'none';
        }
    });
}

// 검색 실행 함수
async function performSearch() {
    const query = queryInput.value.trim();
    const maxDocuments = parseInt(maxDocumentsInput.value);
    const includeImages = includeImagesCheckbox.checked;

    if (!query) {
        showError('질문을 입력해주세요.');
        return;
    }

    // 검색 요청 데이터
    const requestData = {
        query: query,
        max_documents: isNaN(maxDocuments) ? 3 : maxDocuments,
        include_images: includeImages
    };

    try {
        showLoading(true);
        hideError();
        hideAnswerSection();

        // API 호출
        const response = await fetch(`${API_BASE_URL}/api/search`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || '답변 생성 중 오류가 발생했습니다.');
        }

        const data = await response.json();
        displayAnswer(data);
    } catch (error) {
        showError(error.message || '검색 중 오류가 발생했습니다.');
    } finally {
        showLoading(false);
    }
}

// 답변 표시 함수
function displayAnswer(data) {
    if (!data.answer) {
        showError('생성된 답변이 없습니다.');
        return;
    }

    // 답변 내용 표시
    mainAnswer.innerHTML = '';
    const paragraphs = data.answer.split('\n\n');
    
    paragraphs.forEach(paragraph => {
        if (!paragraph.trim()) return;
        
        const p = document.createElement('p');
        p.innerHTML = formatText(paragraph);
        mainAnswer.appendChild(p);
    });

    // 소스 문서 표시
    sourceDocuments.innerHTML = '';
    
    if (data.source_documents && data.source_documents.length > 0) {
        data.source_documents.forEach(doc => {
            const docElement = createSourceDocumentElement(doc);
            sourceDocuments.appendChild(docElement);
        });
    } else {
        sourceDocuments.innerHTML = '<div class="no-results">참조 문서 정보가 없습니다.</div>';
    }

    // 답변 섹션 표시
    showAnswerSection();
}

// 소스 문서 요소 생성
function createSourceDocumentElement(doc) {
    const docElement = document.createElement('div');
    docElement.className = 'source-document';

    // 헤더 (문서명 + 유사도)
    const header = document.createElement('div');
    header.className = 'source-header';

    const title = document.createElement('div');
    title.className = 'source-title';
    title.textContent = `${doc.folder_name || '문서'}`;
    if (doc.page_number) {
        title.textContent += ` (페이지 ${doc.page_number})`;
    }
    header.appendChild(title);

    if (doc.searchScore) {
        const score = document.createElement('div');
        score.className = 'source-score';
        score.textContent = `유사도: ${doc.searchScore.toFixed(2)}`;
        header.appendChild(score);
    }

    docElement.appendChild(header);

    // 요약 (있는 경우)
    if (doc.summary) {
        const summary = document.createElement('div');
        summary.className = 'source-summary';
        summary.textContent = doc.summary;
        docElement.appendChild(summary);
    }

    // 텍스트 (문서 내용)
    if (doc.text) {
        const textPreview = doc.text.length > 300 ? doc.text.substring(0, 300) + '...' : doc.text;
        const text = document.createElement('div');
        text.className = 'source-text';
        text.textContent = textPreview;
        docElement.appendChild(text);
    }

    // 이미지 (있는 경우)
    if (doc.images && doc.images.length > 0) {
        const imagesContainer = document.createElement('div');
        imagesContainer.className = 'source-images';

        // 최대 3개 이미지만 표시
        doc.images.slice(0, 3).forEach((img, index) => {
            try {
                const imgElement = document.createElement('img');
                imgElement.className = 'source-image';
                imgElement.src = img.image || img;
                imgElement.alt = `이미지 ${index + 1}`;
                
                // 이미지 클릭 시 모달 표시
                imgElement.addEventListener('click', function() {
                    showImageModal(img.image || img, img.description || '');
                });
                
                imagesContainer.appendChild(imgElement);
            } catch (e) {
                console.error('이미지 처리 오류:', e);
            }
        });

        // 더 많은 이미지가 있는 경우 표시
        if (doc.images.length > 3) {
            const moreImages = document.createElement('div');
            moreImages.className = 'more-images';
            moreImages.textContent = `외 ${doc.images.length - 3}개 이미지`;
            imagesContainer.appendChild(moreImages);
        }

        docElement.appendChild(imagesContainer);
    }

    return docElement;
}

// 이미지 모달 표시
function showImageModal(imageUrl, description) {
    modalImage.src = imageUrl;
    modalCaption.textContent = description || '';
    imageModal.style.display = 'block';
}

// 텍스트 포맷 함수
function formatText(text) {
    if (!text) return '';
    // 줄바꿈을 <br> 태그로 변환
    return text.replace(/\n/g, '<br>');
}

// 로딩 표시 함수
function showLoading(show) {
    loading.style.display = show ? 'block' : 'none';
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

// 문서가 로드될 때 초기화
document.addEventListener('DOMContentLoaded', initSearchUI);