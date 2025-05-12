import logging
import json
import numpy as np
from typing import List, Dict, Any, Optional, Union, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class DocumentSearchEngine:
    """문서 검색 엔진 클래스"""

    def __init__(self, config: Dict[str, Any]):
        """
        검색 엔진 초기화

        Args:
            config: 애플리케이션 설정
        """
        self.config = config
        self.cosmos_client = self._init_cosmos_client(config['cosmos'])
        self.openai_client = self._init_openai_client(config['openai'])

        self.database_id = config['cosmos'].get('database', 'SKEP_AIPLATFORM_LOCAL')
        self.collection_name = config['cosmos'].get('collection', 'welfare')
        self.embedding_field = 'combined_embedding'

        self.embedding_model = config['openai'].get('embedding_model', 'text-embedding-3-small')
        self.chat_model = config['openai'].get('chat_model', 'gpt-4.1')

        self.database = self.cosmos_client[self.database_id] if self.cosmos_client else None
        self.collection = self.database[self.collection_name] if self.database else None

    def _init_cosmos_client(self, cosmos_config: Dict[str, str]) -> Any:
        """
        Cosmos DB 클라이언트 초기화

        Args:
            cosmos_config: Cosmos DB 설정

        Returns:
            MongoDB 클라이언트 또는 None
        """
        try:
            from pymongo import MongoClient
            connection_string = cosmos_config.get('connection_string')

            if not connection_string:
                logger.error("Cosmos DB 연결 문자열이 설정되지 않았습니다.")
                return None

            client = MongoClient(
                connection_string,
                connectTimeoutMS=30000,
                socketTimeoutMS=30000
            )
            logger.info("Cosmos DB 클라이언트 초기화 성공")
            return client
        except ImportError:
            logger.error("pymongo 패키지가 설치되지 않았습니다.")
            return None
        except Exception as e:
            logger.error(f"Cosmos DB 클라이언트 초기화 오류: {e}")
            return None

    def _init_openai_client(self, openai_config: Dict[str, str]) -> Any:
        """
        Azure OpenAI 클라이언트 초기화

        Args:
            openai_config: OpenAI 설정

        Returns:
            OpenAI 클라이언트 또는 None
        """
        try:
            from openai import AzureOpenAI

            endpoint = openai_config.get('endpoint')
            api_key = openai_config.get('api_key')
            api_version = openai_config.get('api_version', '2025-01-01-preview')

            if not endpoint or not api_key:
                logger.error("Azure OpenAI 엔드포인트 또는 API 키가 설정되지 않았습니다.")
                return None

            client = AzureOpenAI(
                azure_endpoint=endpoint,
                api_key=api_key,
                api_version=api_version
            )
            logger.info("Azure OpenAI 클라이언트 초기화 성공")
            return client
        except ImportError:
            logger.error("openai 패키지가 설치되지 않았습니다.")
            return None
        except Exception as e:
            logger.error(f"OpenAI 클라이언트 초기화 오류: {e}")
            return None

    def generate_embedding(self, text: str) -> List[float]:
        """
        텍스트에 대한 임베딩 벡터 생성

        Args:
            text: 임베딩할 텍스트

        Returns:
            임베딩 벡터
        """
        if not self.openai_client:
            logger.error("OpenAI 클라이언트가 초기화되지 않았습니다.")
            return np.zeros(1536).tolist()  # 기본 차원 수는 1536

        try:
            text = text.replace("\n", " ").strip()
            if not text:
                logger.warning("임베딩할 텍스트가 비어 있습니다.")
                return np.zeros(1536).tolist()

            if len(text) > 8000:
                logger.info(f"임베딩 텍스트가 너무 깁니다. {len(text)} -> 8000자로 제한됩니다.")
                text = text[:8000]

            response = self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=text
            )

            return response.data[0].embedding
        except Exception as e:
            logger.error(f"임베딩 생성 중 오류 발생: {e}")
            return np.zeros(1536).tolist()

    def search(self, query: str, top_k: int = 3, filter_options: Optional[Dict[str, Any]] = None) -> List[
        Dict[str, Any]]:
        """
        벡터 유사도 검색 수행

        Args:
            query: 검색 쿼리
            top_k: 반환할 결과 수
            filter_options: 검색 필터 옵션

        Returns:
            검색 결과 목록
        """
        if not self.collection:
            logger.error("Cosmos DB 컬렉션이 초기화되지 않았습니다.")
            return []

        try:
            query_embedding = self.generate_embedding(query)

            search_pipeline = self._build_search_pipeline(query_embedding, top_k, filter_options)

            results = list(self.collection.aggregate(search_pipeline))

            processed_results = self._process_search_results(results)

            logger.info(f"검색 결과: {len(processed_results)}개 문서 찾음")
            return processed_results

        except Exception as e:
            logger.error(f"검색 중 오류 발생: {e}")
            return []

    def _build_search_pipeline(self, query_embedding: List[float], top_k: int,
                               filter_options: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        검색 파이프라인 구성

        Args:
            query_embedding: 쿼리 임베딩 벡터
            top_k: 반환할 결과 수
            filter_options: 검색 필터 옵션

        Returns:
            MongoDB 집계 파이프라인
        """
        pipeline = [
            {
                "$search": {
                    "cosmosSearch": {
                        "vector": query_embedding,
                        "path": self.embedding_field,
                        "k": top_k * 2  # 후처리를 위해 2배 많은 결과 조회
                    },
                    "returnStoredSource": True
                }
            },
            {
                "$addFields": {
                    "searchScore": {"$meta": "searchScore"}
                }
            }
        ]

        if filter_options:
            match_stage = {"$match": {}}

            if "is_consolidated" in filter_options:
                match_stage["$match"]["is_consolidated"] = filter_options["is_consolidated"]

            if "folder_name" in filter_options:
                match_stage["$match"]["folder_name"] = filter_options["folder_name"]

            if "exclude_exceptions" in filter_options and filter_options["exclude_exceptions"]:
                match_stage["$match"]["is_exception_doc"] = {"$ne": True}

            pipeline.append(match_stage)

        pipeline.extend([
            {"$sort": {"searchScore": -1}},
            {"$limit": top_k}
        ])

        return pipeline

    def _process_search_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        검색 결과 처리

        Args:
            results: 검색 결과 목록

        Returns:
            처리된 검색 결과
        """
        processed_results = []

        for result in results:
            processed = {
                "id": result.get("_id", ""),
                "folder_name": result.get("folder_name", ""),
                "page_number": result.get("page_number", ""),
                "searchScore": result.get("searchScore", 0.0)
            }

            if "description" in result:
                processed["text"] = result["description"]
            elif "full_text" in result:
                processed["text"] = result["full_text"]
            else:
                processed["text"] = ""

            processed["content_analysis"] = self._extract_content_analysis(result)

            processed["images"] = self._extract_images(result)

            processed_results.append(processed)

        return processed_results

    def _extract_content_analysis(self, result: Dict[str, Any]) -> Dict[str, str]:
        """
        문서 분석 정보 추출

        Args:
            result: 검색 결과 문서

        Returns:
            분석 정보
        """
        analysis = {}

        if "content_analysis" in result:
            try:
                if isinstance(result["content_analysis"], str):
                    analysis = json.loads(result["content_analysis"])
                elif isinstance(result["content_analysis"], dict):
                    analysis = result["content_analysis"]
            except json.JSONDecodeError:
                logger.warning(f"콘텐츠 분석 JSON 파싱 실패: {result['content_analysis'][:50]}...")
            except Exception as e:
                logger.warning(f"콘텐츠 분석 추출 오류: {e}")

        if "key_information" in result:
            analysis["key_information"] = result["key_information"]
        elif "key_information" not in analysis:
            analysis["key_information"] = ""

        return analysis

    def _extract_images(self, result: Dict[str, Any]) -> List[str]:
        """
        문서 이미지 추출

        Args:
            result: 검색 결과 문서

        Returns:
            이미지 URL 목록
        """
        images = []

        if "all_images" in result and isinstance(result["all_images"], list):
            images.extend(result["all_images"])

        elif "images" in result and isinstance(result["images"], list):
            images.extend(result["images"])

        return list(dict.fromkeys(images))

    def generate_answer(self, query: str, search_results: List[Dict[str, Any]]) -> str:
        """
        검색 결과를 바탕으로 답변 생성

        Args:
            query: 사용자 질문
            search_results: 검색 결과 목록

        Returns:
            생성된 답변
        """
        if not self.openai_client:
            logger.error("OpenAI 클라이언트가 초기화되지 않았습니다.")
            return "답변을 생성할 수 없습니다. OpenAI 서비스에 연결할 수 없습니다."

        if not search_results:
            return "질문과 관련된 문서를 찾을 수 없습니다."

        try:
            context = self._build_answer_context(search_results)

            messages = [
                {
                    "role": "system",
                    "content": """
                    당신은 조직 내 정보를 제공하는 도우미입니다.
                    주어진 여러 문서 정보를 종합하여 사용자 질문에 포괄적으로 답변하세요.
                    여러 문서의 정보를 통합하여 일관된 답변을 제공하세요.
                    답변은 명확하고 구조적으로 작성하세요.
                    여러 문서 간에 내용이 충돌하는 경우 가장 관련성이 높은 정보를 우선시하세요.
                    """
                },
                {
                    "role": "user",
                    "content": f"질문: {query}\n\n참고 문서:\n{context}"
                }
            ]

            response = self.openai_client.chat.completions.create(
                model=self.chat_model,
                messages=messages,
                temperature=0.7,
                max_tokens=1500
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"답변 생성 중 오류 발생: {e}")
            return f"답변을 생성하는 중 오류가 발생했습니다: {str(e)}"

    def _build_answer_context(self, search_results: List[Dict[str, Any]]) -> str:
        """
        답변 생성용 컨텍스트 구성

        Args:
            search_results: 검색 결과 목록

        Returns:
            컨텍스트 문자열
        """
        context = ""

        for idx, doc in enumerate(search_results):
            folder_name = doc.get("folder_name", "")
            page_number = doc.get("page_number", "")
            text = doc.get("text", "")
            similarity = doc.get("searchScore", 0.0)

            analysis = doc.get("content_analysis", {})
            key_info = analysis.get("key_information", "")

            context += f"\n문서 {idx + 1}: {folder_name}"
            if page_number:
                context += f" (페이지 {page_number})"

            context += f"\n유사도: {similarity:.4f}"

            if key_info:
                context += f"\n핵심 정보: {key_info}"

            if text:
                if len(text) > 1000:
                    truncated_text = text[:1000] + "..."
                else:
                    truncated_text = text

                context += f"\n내용: {truncated_text}\n"

            images = doc.get("images", [])
            if images:
                context += f"\n이미지 포함: {len(images)}개\n"

        return context

    def find_document(self, filter_query: Dict[str, Any], limit: int = 10) -> List[Dict[str, Any]]:
        """
        필터 조건으로 문서 검색

        Args:
            filter_query: 필터 조건
            limit: 최대 결과 수

        Returns:
            검색 결과 목록
        """
        if not self.collection:
            logger.error("Cosmos DB 컬렉션이 초기화되지 않았습니다.")
            return []

        try:
            results = list(self.collection.find(filter_query).limit(limit))
            return results
        except Exception as e:
            logger.error(f"문서 검색 오류: {e}")
            return []

    def upsert_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """
        문서 업데이트 또는 삽입

        Args:
            document: 문서 데이터

        Returns:
            업데이트된 문서
        """
        if not self.collection:
            logger.error("Cosmos DB 컬렉션이 초기화되지 않았습니다.")
            raise Exception("데이터베이스 연결이 설정되지 않았습니다.")

        try:
            if '_id' not in document:
                import hashlib
                doc_string = json.dumps(document, sort_keys=True)
                document['_id'] = hashlib.md5(doc_string.encode()).hexdigest()

            if self.embedding_field not in document or not document[self.embedding_field]:
                text_to_embed = f"폴더: {document.get('folder_name', '')}, 페이지: {document.get('page_number', '')}, 설명: {document.get('description', '')}"
                document[self.embedding_field] = self.generate_embedding(text_to_embed)

            document['updated_at'] = datetime.now()
            if 'created_at' not in document:
                document['created_at'] = document['updated_at']

            self.collection.replace_one(
                {"_id": document['_id']},
                document,
                upsert=True
            )

            logger.info(f"문서 업서트 성공: {document['_id']}")
            return document

        except Exception as e:
            logger.error(f"문서 업서트 중 오류 발생: {e}")
            raise

    def migrate_to_document_structure_in_place(self, exclude_folders: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        페이지 단위 문서를 문서 단위로 마이그레이션

        Args:
            exclude_folders: 제외할 폴더 목록

        Returns:
            마이그레이션 결과
        """
        if not self.collection:
            logger.error("Cosmos DB 컬렉션이 초기화되지 않았습니다.")
            return {"error": "데이터베이스 연결이 설정되지 않았습니다."}

        if exclude_folders is None:
            exclude_folders = ['복리후생_및_기타지원제도']

        try:
            all_pages = list(self.collection.find({"is_consolidated": {"$ne": True}}))
            logger.info(f"총 {len(all_pages)}개의 페이지 데이터를 불러왔습니다.")

            folder_groups = self._group_pages_by_folder(all_pages, exclude_folders)
            logger.info(f"총 {len(folder_groups)}개의 문서 그룹이 생성되었습니다.")

            batch_size = 10
            batches = [list(folder_groups.items())[i:i + batch_size]
                       for i in range(0, len(folder_groups), batch_size)]

            processed_count = 0
            for batch_idx, batch in enumerate(batches):
                logger.info(f"배치 {batch_idx + 1}/{len(batches)} 처리 중...")

                for folder_name, pages in batch:
                    try:
                        pages.sort(key=lambda p: self._safe_int(p.get('page_number', 0)))

                        consolidated_doc = self._create_consolidated_document(folder_name, pages)

                        self.collection.replace_one(
                            {'_id': consolidated_doc['_id']},
                            consolidated_doc,
                            upsert=True
                        )

                        processed_count += 1
                    except Exception as e:
                        logger.error(f"문서 '{folder_name}' 처리 중 오류 발생: {e}")

            for folder_name in exclude_folders:
                self.collection.update_many(
                    {"folder_name": folder_name},
                    {"$set": {"is_exception_doc": True}}
                )

            return {
                "total_folders": len(folder_groups),
                "processed_documents": processed_count,
                "collection_name": self.collection.name
            }

        except Exception as e:
            logger.error(f"마이그레이션 중 오류 발생: {e}")
            return {"error": str(e)}

    def _group_pages_by_folder(self, pages: List[Dict[str, Any]],
                               exclude_folders: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """
        페이지를 폴더별로 그룹화

        Args:
            pages: 페이지 목록
            exclude_folders: 제외할 폴더 목록

        Returns:
            폴더별 페이지 그룹
        """
        folder_groups = {}

        for page in pages:
            folder_name = page.get('folder_name', '')

            if folder_name in exclude_folders:
                continue

            if folder_name not in folder_groups:
                folder_groups[folder_name] = []

            page_info = {
                'page_number': page.get('page_number', ''),
                'description': page.get('description', '')
            }

            if 'images' in page and page['images']:
                page_info['images'] = page['images']

            folder_groups[folder_name].append(page_info)

        return folder_groups

    def _create_consolidated_document(self, folder_name: str,
                                      pages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        통합 문서 생성

        Args:
            folder_name: 폴더명
            pages: 페이지 목록

        Returns:
            통합 문서
        """
        full_text = f"문서: {folder_name}\n"
        all_images = []

        for page in pages:
            page_num = page.get('page_number', '')
            desc = page.get('description', '')
            full_text += f"페이지 {page_num}: {desc}\n"

            if 'images' in page and page['images']:
                all_images.extend(self._extract_image_data(page['images']))

        document = {
            '_id': f"doc_{folder_name}",
            'folder_name': folder_name,
            'pages': pages,
            'full_text': full_text,
            'all_images': all_images,
            'is_consolidated': True,
            'created_at': datetime.now()
        }

        document[self.embedding_field] = self.generate_embedding(full_text)

        return document

    def _extract_image_data(self, images: List[Any]) -> List[str]:
        """
        이미지 데이터 추출

        Args:
            images: 이미지 데이터 목록

        Returns:
            추출된 이미지 URL 목록
        """
        result = []

        if not images:
            return result

        for img in images:
            if isinstance(img, dict) and 'image' in img:
                result.append(img['image'])
            elif isinstance(img, str):
                result.append(img)

        return result

    def _safe_int(self, value: Any) -> int:
        """
        안전하게 정수로 변환

        Args:
            value: 변환할 값

        Returns:
            정수 값
        """
        if not value:
            return 0

        if isinstance(value, int):
            return value

        try:
            clean_value = ''.join(c for c in str(value) if c.isdigit())
            if clean_value:
                return int(clean_value)
            return 0
        except:
            return 0