import os
import gc
from pathlib import Path
from typing import Dict, Any
from sqlalchemy.orm import Session

from services.ingestion_service import IngestionService
from services.chunking_service import ChunkingService
from services.embedding_service import EmbeddingService
from database.vector_store import VectorStore
from models.document import Document
from core.logging_config import get_logger

logger = get_logger("pipeline")


def process_document_pipeline(db: Session, filename: str) -> Dict[str, Any]:
    try:
        file_path = Path("data") / filename
        
        if not file_path.exists():
            return {
                "success": False,
                "error": f"File not found: {filename}"
            }
        
        existing = db.query(Document).filter(
            Document.original_filename == filename
        ).first()

        if existing is not None:
            is_processed_value = getattr(existing, 'is_processed', False)
            if is_processed_value:
                return {
                    "success": True,
                    "skipped": True,
                    "message": f"Document already processed: {filename}"
                }

        ingestion_service = IngestionService(db)
        with open(file_path, 'rb') as f:
            content = f.read()

        document = ingestion_service.ingest_document_sync(content, filename)

        chunking_service = ChunkingService(db)
        chunks = chunking_service.chunk_document(document)
        logger.info(f"Created {len(chunks)} chunks")

        # Force garbage collection after chunking
        gc.collect()

        embedding_service = EmbeddingService(db)
        doc_id_value = getattr(document, 'id', None)
        if doc_id_value is not None:
            logger.info(f"Generating embeddings for {len(chunks)} chunks...")
            embedding_service.generate_embeddings_for_document(document_id=doc_id_value)
            
            # Force garbage collection after embeddings
            gc.collect()

        vector_store = VectorStore(db)
        vector_store.sync_embeddings_to_vector(batch_size=len(chunks))
        
        # Final garbage collection
        gc.collect()

        return {
            "success": True,
            "skipped": False,
            "chunks_count": len(chunks),
            "embeddings_count": len(chunks),
            "message": f"Successfully processed: {filename}"
        }

    except Exception as e:
        logger.error(f"Failed to process {filename}: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }
