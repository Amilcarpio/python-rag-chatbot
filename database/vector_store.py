from typing import List, Tuple, Dict
from sqlalchemy.orm import Session
from sqlalchemy import text, func
import json

from models.chunk import Chunk

class VectorStore:
    def __init__(self, db: Session):
        self.db = db

    def sync_embeddings_to_vector(self, batch_size: int = 100) -> Dict[str, int]:
        chunks = self.db.query(Chunk).filter(
            Chunk.embedding.isnot(None),
            Chunk.embedding_vector.is_(None)
        ).limit(batch_size).all()

        if not chunks:
            return {'synced': 0, 'total_pending': 0}

        synced = 0
        for chunk in chunks:
            try:
                embedding_list = json.loads(str(chunk.embedding))
                embedding_str = '[' + ','.join(map(str, embedding_list)) + ']'

                self.db.execute(
                    text("UPDATE chunks SET embedding_vector = :vec WHERE id = :id"),
                    {"vec": embedding_str, "id": chunk.id}
                )
                synced += 1
            except Exception as e:
                print(f"Error syncing chunk {chunk.id}: {e}")
                continue

        self.db.commit()

        pending = self.db.query(Chunk).filter(
            Chunk.embedding.isnot(None),
            Chunk.embedding_vector.is_(None)
        ).count()

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

        chunks_with_vector = self.db.query(Chunk).filter(
            Chunk.embedding_vector.isnot(None)
        ).count()

        docs_with_embeddings = self.db.query(
            func.count(func.distinct(Chunk.document_id))
        ).filter(
            Chunk.embedding_vector.isnot(None)
        ).scalar()

        return {
            'total_chunks': total_chunks,
            'chunks_with_vectors': chunks_with_vector,
            'chunks_pending': total_chunks - chunks_with_vector,
            'completion_rate': round(
                (chunks_with_vector / total_chunks * 100) if total_chunks > 0 else 0,
                2
            ),
            'documents_indexed': docs_with_embeddings or 0
        }
