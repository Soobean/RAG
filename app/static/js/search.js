// 검색 관련 기능
const API_BASE_URL = 'http://localhost:8000/api';

// 검색 수행 함수
async function performSearch(query, maxDocuments, includeImages = true) {
    try {
        showLoading(true);
        hideError();
        hideAnswerSection();

        const requestData = {
            query: query,
            max_documents: parseInt(maxDocuments || 3),
            include_images: includeImages
        };

        // API 호출
        const response = await fetch(`${API_BASE_URL}/search/query`, {
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

        return await response.json();
    } catch (error) {
        showError(error.message);
        return null;
    } finally {
        showLoading(false);
    }
}

// 문서 목록 조회 함수
async function listDocuments() {
    try {
        const response = await fetch(`${API_BASE_URL}/documents/list`);

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || '문서 목록 조회 중 오류가 발생했습니다.');
        }

        return await response.json();
    } catch (error) {
        console.error('문서 목록 조회 오류:', error);
        return { documents: [], total: 0 };
    }
}

// 문서 조회 함수
async function getDocument(folderName) {
    try {
        const response = await fetch(`${API_BASE_URL}/documents/${encodeURIComponent(folderName)}`);

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || '문서 조회 중 오류가 발생했습니다.');
        }

        return await response.json();
    } catch (error) {
        console.error('문서 조회 오류:', error);
        return null;
    }
}

// 텍스트 포맷 함수 (줄바꿈 유지)
function formatText(text) {
    if (!text) return '';
    // 줄바꿈을 <br> 태그로 변환
    return text.replace(/\n/g, '<br>');
}