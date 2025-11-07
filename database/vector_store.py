from typing import List, Tuple, Dict
from sqlalchemy.orm import Session
from sqlalchemy import text, func
import json

from models.chunk import Chunk

class VectorStore:
    def __init__(self, db: Session):
        self.db = db

    def sync_embeddings_to_vector(self, batch_size: int = 100) -> Dict[str, int]:
        query = text("""
            SELECT id, embedding
            FROM chunks
            WHERE embedding IS NOT NULL
                AND embedding_vector IS NULL
            LIMIT :limit
        """)
        
        results = self.db.execute(query, {"limit": batch_size}).fetchall()

        if not results:
            pending_query = text("""
                SELECT COUNT(*)
                FROM chunks
                WHERE embedding IS NOT NULL
                    AND embedding_vector IS NULL
            """)
            pending = self.db.execute(pending_query).scalar() or 0
            return {'synced': 0, 'total_pending': pending}

        synced = 0
        for row in results:
            try:
                chunk_id = row.id
                embedding_json = row.embedding
                
                embedding_list = json.loads(str(embedding_json))
                embedding_str = '[' + ','.join(map(str, embedding_list)) + ']'

                self.db.execute(
                    text("UPDATE chunks SET embedding_vector = CAST(:vec AS vector) WHERE id = :id"),
                    {"vec": embedding_str, "id": chunk_id}
                )
                synced += 1
            except Exception as e:
                from core.logging_config import get_logger
                logger = get_logger("vector_store")
                logger.error(f"Error syncing chunk {chunk_id}: {e}")
                continue

        self.db.commit()

        pending_query = text("""
            SELECT COUNT(*)
            FROM chunks
            WHERE embedding IS NOT NULL
                AND embedding_vector IS NULL
        """)
        pending = self.db.execute(pending_query).scalar() or 0

        return {'synced': synced, 'total_pending': pending}

    def similarity_search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        min_similarity: float = 0.0
    ) -> List[Tuple[Chunk, float]]:
        embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
        max_distance = 2 * (1 - min_similarity)

        query = text("""
            SELECT
                id,
                content,
                document_id,
                chunk_index,
                embedding_vector <=> :query_vec AS distance
            FROM chunks
            WHERE embedding_vector IS NOT NULL
                AND embedding_vector <=> :query_vec <= :max_dist
            ORDER BY embedding_vector <=> :query_vec
            LIMIT :limit
        """)

        results = self.db.execute(
            query,
            {
                "query_vec": embedding_str,
                "max_dist": max_distance,
                "limit": top_k
            }
        ).fetchall()

        chunk_results = []
        for row in results:
            chunk = self.db.query(Chunk).filter(Chunk.id == row.id).first()
            if chunk:
                similarity = 1 - (row.distance / 2)
                chunk_results.append((chunk, similarity))

        return chunk_results

    def get_stats(self) -> Dict:
        total_chunks = self.db.query(Chunk).count()

        chunks_with_vector_query = text("""
            SELECT COUNT(*)
            FROM chunks
            WHERE embedding_vector IS NOT NULL
        """)
        chunks_with_vector = self.db.execute(chunks_with_vector_query).scalar() or 0

        docs_with_embeddings_query = text("""
            SELECT COUNT(DISTINCT document_id)
            FROM chunks
            WHERE embedding_vector IS NOT NULL
        """)
        docs_with_embeddings = self.db.execute(docs_with_embeddings_query).scalar() or 0

        return {
            'total_chunks': total_chunks,
            'chunks_with_vectors': chunks_with_vector,
            'chunks_pending': total_chunks - chunks_with_vector,
            'completion_rate': round(
                (chunks_with_vector / total_chunks * 100) if total_chunks > 0 else 0,
                2
            ),
            'documents_indexed': docs_with_embeddings
        }
