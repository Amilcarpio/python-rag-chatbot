from typing import List, Dict, Optional
from sqlalchemy.orm import Session

from database.vector_store import VectorStore
from services.embedding_service import EmbeddingService
from models.chunk import Chunk
from models.document import Document
from core.config import settings

class RetrievalService:

    def __init__(self, db: Session):
        self.db = db
        self.vector_store = VectorStore(db)
        self.embedding_service = EmbeddingService(db)

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        min_similarity: Optional[float] = None
    ) -> List[Dict]:

        if top_k is None:
            top_k = settings.TOP_K_RESULTS
        if min_similarity is None:
            min_similarity = settings.MIN_SIMILARITY

        query_embedding = self.embedding_service.generate_query_embedding(query)

        chunk_results = self.vector_store.similarity_search(
            query_embedding=query_embedding,
            top_k=top_k * 2,
            min_similarity=min_similarity
        )

        if not chunk_results:
            return []

        seen_docs = set()
        deduplicated = []

        for chunk, similarity in chunk_results:
            if chunk.document_id not in seen_docs:
                seen_docs.add(chunk.document_id)
                deduplicated.append((chunk, similarity))

            if len(deduplicated) >= top_k:
                break

        results = []
        for chunk, similarity in deduplicated:
            document = self.db.query(Document).filter(
                Document.id == chunk.document_id
            ).first()

            result = {
                'chunk': chunk,
                'similarity': round(similarity, 3),
                'document': document,
                'chunk_index': chunk.chunk_index,
                'content': str(chunk.content),
                'full_context': str(chunk.content)
            }

            results.append(result)

        return results

    def retrieve_with_metadata(
        self,
        query: str,
        top_k: Optional[int] = None
    ) -> Dict:

        results = self.retrieve(query, top_k=top_k)

        if not results:
            return {
                'results': [],
                'total_found': 0,
                'query_tokens': self.embedding_service.count_tokens(query),
                'avg_similarity': 0.0
            }

        avg_similarity = sum(r['similarity'] for r in results) / len(results)
        total_context_tokens = sum(
            self.embedding_service.count_tokens(r['full_context'])
            for r in results
        )

        return {
            'results': results,
            'total_found': len(results),
            'query_tokens': self.embedding_service.count_tokens(query),
            'context_tokens': total_context_tokens,
            'avg_similarity': round(avg_similarity, 3),
            'min_similarity': min(r['similarity'] for r in results),
            'max_similarity': max(r['similarity'] for r in results)
        }
