import numpy as np


class EmbeddingManager:
    def __init__(self, openai_client, embedding_model="text-embedding-3-small"):
        """
        임베딩 관리자 초기화
        :param openai_client: OpenAI 클라이언트
        :param embedding_model: 임베딩 모델명
        """
        self.openai_client = openai_client
        self.embedding_model = embedding_model
        self.embedding_dim = 1536

    def generate_embedding(self, text):
        """
        텍스트 임베딩 생성
        :param text: 임베딩할 텍스트
        :return: 임베딩 벡터
        """
        if not text or not text.strip():
            return np.zeros(self.embedding_dim).tolist()

        text = text.replace("\n", " ")[:8000]  # 텍스트 길이 제한

        try:
            response = self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"임베딩 생성 오류: {e}")
            return np.zeros(self.embedding_dim).tolist()

    def create_document_embedding(self, document):
        """
        문서 데이터를 바탕으로 최적화된 임베딩 생성
        :param document: 문서 데이터
        :return: 문서 임베딩
        """
        folder_name = document.get("folder_name", "")
        page_number = document.get("page_number", "")
        description = document.get("description", "")
        key_info = document.get("key_information", "")

        embedding_text = f"""
        문서: {folder_name}
        페이지: {page_number}
        내용: {description[:3000]}
        핵심 정보: {key_info}
        """

        return self.generate_embedding(embedding_text)

    def calculate_similarity(self, embedding1, embedding2):
        """
        두 임베딩 간의 코사인 유사도 계산
        :param embedding1: 첫 번째 임베딩
        :param embedding2: 두 번째 임베딩
        :return: 코사인 유사도 점수
        """
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)

        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0

        return dot_product / (norm1 * norm2)