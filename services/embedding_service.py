import json
import time
import gc
from typing import List, Optional, Dict, Any
import numpy as np
from sqlalchemy.orm import Session
from openai import OpenAI
import tiktoken

from models.chunk import Chunk
from models.document import Document
from core.config import settings

class EmbeddingService:

    def __init__(self, db: Session):
        self.db = db
        
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not configured. Please set it in .env file.")
        
        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            timeout=60.0
        )
        self.model = settings.EMBEDDING_MODEL
        
        try:
            self.encoding = tiktoken.encoding_for_model(self.model)
        except:
            self.encoding = tiktoken.encoding_for_model("text-embedding-ada-003")

    def generate_embeddings_for_document(
        self,
        document_id: int,
        batch_size: int = 5
    ) -> Dict[str, Any]:

        chunks = self.db.query(Chunk).filter(
            Chunk.document_id == document_id,
            Chunk.embedding.is_(None)
        ).all()

        if not chunks:
            return {
                'chunks_processed': 0,
                'total_tokens': 0,
                'estimated_cost': 0,
                'message': 'No chunks to process'
            }

        total_tokens = 0
        chunks_processed = 0
        start_time = time.time()
        total_batches = (len(chunks) + batch_size - 1) // batch_size

        from core.logging_config import get_logger
        logger = get_logger("embedding")
        
        logger.info(f"Processing {len(chunks)} chunks in {total_batches} batch(es)...")

        for i in range(0, len(chunks), batch_size):
            batch_num = (i // batch_size) + 1
            batch = chunks[i:i + batch_size]

            texts = [str(chunk.content) for chunk in batch]

            batch_tokens = sum(len(self.encoding.encode(text)) for text in texts)
            total_tokens += batch_tokens

            try:
                logger.info(f"  Batch {batch_num}/{total_batches}: Generating embeddings for {len(batch)} chunks ({batch_tokens} tokens)...")
                embeddings = self._generate_embeddings_batch(texts)
                logger.info(f"  Batch {batch_num}/{total_batches}: ✓ Embeddings received from OpenAI")

                for chunk, embedding in zip(batch, embeddings):
                    setattr(chunk, "embedding", json.dumps(embedding))
                    setattr(chunk, "embedding_model", self.model)
                    chunks_processed += 1

                self.db.commit()
                logger.info(f"  Batch {batch_num}/{total_batches}: ✓ Saved to database ({chunks_processed}/{len(chunks)} chunks processed)")

                del embeddings
                gc.collect()

            except Exception as e:
                self.db.rollback()
                logger.error(f"  Batch {batch_num}/{total_batches}: ✗ Error: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                continue

        document = self.db.query(Document).filter(Document.id == document_id).first()
        if document and chunks_processed == len(chunks):
            setattr(document, "is_processed", True)
            setattr(document, "processing_status", "completed")
            self.db.commit()

        elapsed_time = time.time() - start_time
        estimated_cost = (total_tokens / 1000) * 0.0001

        return {
            'chunks_processed': chunks_processed,
            'total_chunks': len(chunks),
            'total_tokens': total_tokens,
            'estimated_cost': round(estimated_cost, 6),
            'elapsed_time': round(elapsed_time, 2),
            'tokens_per_second': round(total_tokens / elapsed_time if elapsed_time > 0 else 0, 2)
        }

    def _generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:

        max_retries = 3
        retry_delay = 1

        for attempt in range(max_retries):
            try:
                from core.logging_config import get_logger
                logger = get_logger("embedding")
                
                if attempt > 0:
                    logger.info(f"    Retry attempt {attempt + 1}/{max_retries}...")
                
                logger.debug(f"    Calling OpenAI API with model: {self.model}")
                response = self.client.embeddings.create(
                    model=self.model,
                    input=texts
                )

                embeddings = [item.embedding for item in response.data]
                logger.debug(f"    ✓ Received {len(embeddings)} embeddings from OpenAI")
                return embeddings

            except Exception as e:
                from core.logging_config import get_logger
                logger = get_logger("embedding")
                logger.warning(f"    API call failed: {str(e)}")
                
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    logger.info(f"    Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"    All retries exhausted. Raising exception.")
                    raise e

        raise Exception("Failed to generate embeddings after all retries")

    def generate_query_embedding(self, query: str) -> List[float]:

        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=[query]
            )
            return response.data[0].embedding

        except Exception as e:
            raise Exception(f"Error generating query embedding: {str(e)}")

    def count_tokens(self, text: str) -> int:

        return len(self.encoding.encode(text))

    def get_embedding_stats(self) -> Dict:

        total_chunks = self.db.query(Chunk).count()
        chunks_with_embedding = self.db.query(Chunk).filter(
            Chunk.embedding.isnot(None)
        ).count()

        return {
            'total_chunks': total_chunks,
            'chunks_with_embedding': chunks_with_embedding,
            'chunks_pending': total_chunks - chunks_with_embedding,
            'completion_rate': round(
                (chunks_with_embedding / total_chunks * 100) if total_chunks > 0 else 0,
                2
            )
        }

    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:

        v1 = np.array(vec1)
        v2 = np.array(vec2)

        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))
