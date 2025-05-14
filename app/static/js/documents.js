/**
 * 문서 관리 관련 JavaScript
 */

// API 기본 URL
const API_BASE_URL = window.location.origin;

// DOM 요소
let uploadForm;
let documentFileInput;
let uploadBtn;
let uploadProgress;
let progressValue;
let progressStatus;
let refreshBtn;
let consolidateBtn;
let documentGrid;

// 초기화 함수
function initDocumentsUI() {
    // DOM 요소 참조
    uploadForm = document.getElementById('upload-form');
    documentFileInput = document.getElementById('document-file');
    uploadBtn = document.getElementById('upload-btn');
    uploadProgress = document.getElementById('upload-progress');
    progressValue = document.getElementById('progress-value');
    progressStatus = document.getElementById('progress-status');
    refreshBtn = document.getElementById('refresh-btn');
    consolidateBtn = document.getElementById('consolidate-btn');
    documentGrid = document.getElementById('document-grid');

    // 이벤트 리스너 설정
    uploadForm.addEventListener('submit', uploadDocument);
    refreshBtn.addEventListener('click', loadDocumentList);
    consolidateBtn.addEventListener('click', consolidateDocuments);

    // 초기 문서 목록 로드
    loadDocumentList();
}

// 문서 업로드 함수
async function uploadDocument(event) {
    event.preventDefault();

    const file = documentFileInput.files[0];
    if (!file) {
        showErrorMessage('파일을 선택해주세요.');
        return;
    }

    // 파일 확장자 확인
    const fileExt = file.name.split('.').pop().toLowerCase();
    if (!['pdf', 'pptx'].includes(fileExt)) {
        showErrorMessage('PDF 또는 PPTX 파일만 업로드 가능합니다.');
        return;
    }

    // 폼 데이터 생성
    const formData = new FormData();
    formData.append('file', file);

    // 콘솔에 파일명 출력하여 확인 (디버깅용)
    console.log("업로드할 파일명:", file.name);

    try {
        // 업로드 시작
        showUploadProgress(true);
        uploadBtn.disabled = true;
        progressValue.style.width = '0%';
        progressStatus.textContent = '업로드 중...';

        // API 호출
        const response = await fetch(`${API_BASE_URL}/api/upload`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || '문서 업로드 중 오류가 발생했습니다.');
        }

        progressValue.style.width = '100%';

        // 결과 처리
        const result = await response.json();
        progressStatus.textContent = result.message || '업로드 완료!';

        // 업로드 성공 후 문서 목록 새로고침
        setTimeout(() => {
            showUploadProgress(false);
            uploadBtn.disabled = false;
            documentFileInput.value = '';
            loadDocumentList();
        }, 2000);

    } catch (error) {
        progressStatus.textContent = `오류: ${error.message || '업로드 실패'}`;
        progressValue.style.width = '100%';
        progressValue.style.backgroundColor = 'var(--error-color)';

        setTimeout(() => {
            showUploadProgress(false);
            uploadBtn.disabled = false;
        }, 3000);
    }
}

// 문서 목록 로드 함수
async function loadDocumentList() {
    try {
        // 로딩 상태 표시
        documentGrid.innerHTML = '<div class="loading-placeholder">문서 로딩 중...</div>';

        // API 호출
        const response = await fetch(`${API_BASE_URL}/api/documents/list`);

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || '문서 목록 로드 중 오류가 발생했습니다.');
        }

        const result = await response.json();

        // 결과 표시
        displayDocumentList(result.documents);

    } catch (error) {
        documentGrid.innerHTML = `<div class="loading-placeholder">문서 로드 오류: ${error.message}</div>`;
    }
}

// 문서 통합 함수
async function consolidateDocuments() {
    const confirmed = await showConfirmModal('문서 통합', '개별 페이지 문서를 통합 문서로 변환하시겠습니까? 이 작업은 시간이 걸릴 수 있습니다.');

    if (!confirmed) return;

    try {
        // 버튼 비활성화
        consolidateBtn.disabled = true;
        consolidateBtn.textContent = '통합 중...';

        // API 호출
        const response = await fetch(`${API_BASE_URL}/api/documents/consolidate`, {
            method: 'POST'
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || '문서 통합 중 오류가 발생했습니다.');
        }

        const result = await response.json();

        // 성공 알림
        alert(result.message || '문서 통합이 완료되었습니다.');

        // 문서 목록 새로고침
        loadDocumentList();

    } catch (error) {
        alert(`오류: ${error.message || '문서 통합 실패'}`);
    } finally {
        // 버튼 상태 복원
        consolidateBtn.disabled = false;
        consolidateBtn.textContent = '문서 통합';
    }
}

// 문서 목록 표시 함수
function displayDocumentList(documents) {
    if (!documents || documents.length === 0) {
        documentGrid.innerHTML = '<div class="loading-placeholder">등록된 문서가 없습니다.</div>';
        return;
    }

    documentGrid.innerHTML = '';

    // 문서 정렬 (생성일 기준 내림차순)
    documents.sort((a, b) => {
        // 생성일이 있는 경우 비교
        if (a.created_at && b.created_at) {
            return new Date(b.created_at) - new Date(a.created_at);
        }
        // 이름 기준 정렬
        return a.folder_name.localeCompare(b.folder_name);
    });

    // 각 문서 카드 생성
    documents.forEach(doc => {
        const cardElement = createDocumentCard(doc);
        documentGrid.appendChild(cardElement);
    });
}

// 문서 카드 요소 생성
function createDocumentCard(doc) {
    const cardElement = document.createElement('div');
    cardElement.className = 'document-card';

    // 카드 헤더
    const header = document.createElement('div');
    header.className = 'card-header';

    const title = document.createElement('h3');
    title.className = 'card-title';
    title.title = doc.folder_name; // 툴팁
    title.textContent = doc.folder_name;

    header.appendChild(title);
    cardElement.appendChild(header);

    // 카드 본문
    const body = document.createElement('div');
    body.className = 'card-body';

    // 문서 정보
    const info = document.createElement('div');
    info.className = 'card-info';

    // 문서 유형
    const typeText = doc.document_type === 'consolidated' ? '통합 문서' : '개별 페이지';
    const type = document.createElement('p');
    type.innerHTML = `<strong>유형:</strong> ${typeText}`;
    info.appendChild(type);

    // 페이지 수
    const pages = document.createElement('p');
    pages.innerHTML = `<strong>페이지:</strong> ${doc.pages_count || 0}페이지`;
    info.appendChild(pages);

    // 생성일
    if (doc.created_at) {
        const created = document.createElement('p');
        created.innerHTML = `<strong>생성일:</strong> ${formatDate(doc.created_at)}`;
        info.appendChild(created);
    }

    body.appendChild(info);

    // 문서 요약 (있는 경우)
    if (doc.document_summary) {
        const summary = document.createElement('div');
        summary.className = 'card-summary';
        summary.textContent = truncateText(doc.document_summary, 100);
        body.appendChild(summary);
    }

    // 카드 액션 버튼
    const actions = document.createElement('div');
    actions.className = 'card-actions';

    // 보기 버튼
    const viewBtn = document.createElement('button');
    viewBtn.className = 'card-btn view';
    viewBtn.textContent = '상세보기';
    viewBtn.addEventListener('click', () => viewDocument(doc.folder_name));
    actions.appendChild(viewBtn);

    // 삭제 버튼
    const deleteBtn = document.createElement('button');
    deleteBtn.className = 'card-btn delete';
    deleteBtn.textContent = '삭제';
    deleteBtn.addEventListener('click', () => deleteDocument(doc.folder_name));
    actions.appendChild(deleteBtn);

    body.appendChild(actions);
    cardElement.appendChild(body);

    return cardElement;
}

// 문서 상세 보기
async function viewDocument(folderName) {
    try {
        // API 호출
        const response = await fetch(`${API_BASE_URL}/api/documents/${encodeURIComponent(folderName)}`);

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || '문서 조회 중 오류가 발생했습니다.');
        }

        const documentData = await response.json();

        // 모달에 문서 정보 표시
        showDocumentModal(documentData);

    } catch (error) {
        alert(`오류: ${error.message || '문서 조회 실패'}`);
    }
}

// 문서 삭제
async function deleteDocument(folderName) {
    const confirmed = await showConfirmModal('문서 삭제', `"${folderName}" 문서를 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.`);

    if (!confirmed) return;

    try {
        // API 호출
        const response = await fetch(`${API_BASE_URL}/api/folder/${encodeURIComponent(folderName)}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || '문서 삭제 중 오류가 발생했습니다.');
        }

        const result = await response.json();

        // 성공 알림
        alert(result.message || '문서가 삭제되었습니다.');

        // 문서 목록 새로고침
        loadDocumentList();

    } catch (error) {
        alert(`오류: ${error.message || '문서 삭제 실패'}`);
    }
}

// 업로드 진행 상태 표시
function showUploadProgress(show) {
    uploadProgress.style.display = show ? 'block' : 'none';
}

// 텍스트 축약 함수
function truncateText(text, maxLength) {
    if (!text) return '';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

// 날짜 포맷 함수
function formatDate(dateString) {
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString('ko-KR', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch (e) {
        return dateString;
    }
}

// 문서가 로드될 때 초기화
document.addEventListener('DOMContentLoaded', initDocumentsUI);