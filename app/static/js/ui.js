/**
 * UI 관련 JavaScript
 */

// 초기화 함수
function initUI() {
    // 탭 전환 기능
    initTabs();

    // 모달 닫기 이벤트
    initModals();
}

// 탭 초기화 및 이벤트 설정
function initTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            // 활성 탭 버튼 스타일 변경
            tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // 탭 컨텐츠 표시/숨김
            const tabId = btn.dataset.tab;
            tabContents.forEach(content => {
                if (content.id === `${tabId}-tab`) {
                    content.classList.add('active');
                } else {
                    content.classList.remove('active');
                }
            });

            // 탭 전환 시 특별 동작
            if (tabId === 'documents') {
                // 문서 목록 로드
                if (typeof loadDocumentList === 'function') {
                    loadDocumentList();
                }
            }
        });
    });
}

// 모달 초기화
function initModals() {
    // 이미지 모달 닫기
    const imageModal = document.getElementById('imageModal');
    const imageClose = document.querySelector('#imageModal .close');

    if (imageClose) {
        imageClose.addEventListener('click', () => {
            imageModal.style.display = 'none';
        });
    }

    // 문서 상세 모달 닫기
    const documentModal = document.getElementById('documentModal');
    const documentClose = document.querySelector('.document-close');

    if (documentClose) {
        documentClose.addEventListener('click', () => {
            documentModal.style.display = 'none';
        });
    }

    // 확인 모달 닫기
    const confirmModal = document.getElementById('confirmModal');
    const confirmClose = document.querySelector('.confirm-close');
    const confirmNo = document.getElementById('confirmNo');

    if (confirmClose) {
        confirmClose.addEventListener('click', () => {
            confirmModal.style.display = 'none';
        });
    }

    if (confirmNo) {
        confirmNo.addEventListener('click', () => {
            confirmModal.style.display = 'none';
        });
    }

    // 모달 외부 클릭시 닫기
    window.addEventListener('click', (event) => {
        if (event.target === imageModal) {
            imageModal.style.display = 'none';
        }
        if (event.target === documentModal) {
            documentModal.style.display = 'none';
        }
        if (event.target === confirmModal) {
            confirmModal.style.display = 'none';
        }
    });
}

// 확인 모달 표시 (Promise 기반)
function showConfirmModal(title, message) {
    return new Promise((resolve) => {
        const confirmModal = document.getElementById('confirmModal');
        const confirmTitle = document.getElementById('confirmTitle');
        const confirmMessage = document.getElementById('confirmMessage');
        const confirmYes = document.getElementById('confirmYes');

        confirmTitle.textContent = title;
        confirmMessage.textContent = message;
        confirmModal.style.display = 'block';

        // 이전 이벤트 리스너 제거
        const newConfirmYes = confirmYes.cloneNode(true);
        confirmYes.parentNode.replaceChild(newConfirmYes, confirmYes);

        // 새 이벤트 리스너 추가
        newConfirmYes.addEventListener('click', () => {
            confirmModal.style.display = 'none';
            resolve(true);
        });

        // '아니오' 버튼 이벤트
        document.getElementById('confirmNo').addEventListener('click', () => {
            confirmModal.style.display = 'none';
            resolve(false);
        });
    });
}

// 문서 상세 모달 표시
function showDocumentModal(documentData) {
    const documentModal = document.getElementById('documentModal');
    const documentTitle = document.getElementById('documentTitle');
    const documentContent = document.getElementById('documentContent');

    // 제목 설정
    documentTitle.textContent = documentData.folder_name || '문서 상세';

    // 콘텐츠 설정
    documentContent.innerHTML = '';

    // 문서 요약
    if (documentData.document_summary) {
        const summary = document.createElement('div');
        summary.className = 'detail-summary';
        summary.innerHTML = `<h4>문서 요약</h4><p>${documentData.document_summary}</p>`;
        documentContent.appendChild(summary);
    }

    // 페이지 정보
    const pagesSection = document.createElement('div');
    pagesSection.className = 'detail-pages';
    pagesSection.innerHTML = `<h4>페이지 (${documentData.pages_count || 0})</h4>`;

    // 페이지 목록
    if (documentData.pages && documentData.pages.length > 0) {
        documentData.pages.forEach((page, index) => {
            const pageElement = document.createElement('div');
            pageElement.className = 'detail-page';

            // 페이지 헤더
            pageElement.innerHTML = `<h5>페이지 ${page.page_number || (index + 1)}</h5>`;

            // 페이지 내용
            if (page.text_content || page.description) {
                const content = document.createElement('p');
                content.textContent = page.text_content || page.description;
                pageElement.appendChild(content);
            }

            // 페이지 이미지
            if (page.images && page.images.length > 0) {
                const imagesContainer = document.createElement('div');
                imagesContainer.className = 'detail-images';

                page.images.forEach((img, imgIndex) => {
                    const imgUrl = img.image || img;
                    const imgDesc = img.description || `이미지 ${imgIndex + 1}`;

                    const imgElement = document.createElement('img');
                    imgElement.className = 'detail-image';
                    imgElement.src = imgUrl;
                    imgElement.alt = imgDesc;
                    imgElement.title = imgDesc;

                    // 이미지 클릭시 모달 표시
                    imgElement.addEventListener('click', () => {
                        const modalImage = document.getElementById('modalImage');
                        const modalCaption = document.getElementById('modalCaption');
                        const imageModal = document.getElementById('imageModal');

                        modalImage.src = imgUrl;
                        modalCaption.textContent = imgDesc;
                        imageModal.style.display = 'block';
                    });

                    imagesContainer.appendChild(imgElement);
                });

                pageElement.appendChild(imagesContainer);
            }

            pagesSection.appendChild(pageElement);
        });
    } else {
        pagesSection.innerHTML += '<p>페이지 정보가 없습니다.</p>';
    }

    documentContent.appendChild(pagesSection);

    // 모달 표시
    documentModal.style.display = 'block';
}

// 에러 표시 함수
function showErrorMessage(message, elementId = 'error-message') {
    const errorElement = document.getElementById(elementId);
    if (errorElement) {
        errorElement.textContent = message;
        errorElement.style.display = 'block';

        // 5초 후 자동으로 숨김
        setTimeout(() => {
            errorElement.style.display = 'none';
        }, 5000);
    }
}

// 문서가 로드될 때 초기화
document.addEventListener('DOMContentLoaded', initUI);