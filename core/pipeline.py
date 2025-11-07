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
    """
    Process a single document: ingest, chunk, embed, and index.
    Optimized to prevent memory leaks by processing in batches and cleaning up.
    """
    ingestion_service = None
    chunking_service = None
    embedding_service = None
    vector_store = None
    document = None
    
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

        logger.info(f"Step 1: Ingesting document {filename}...")
        ingestion_service = IngestionService(db)
        with open(file_path, 'rb') as f:
            content = f.read()

        document = ingestion_service.ingest_document_sync(content, filename, save_to_disk=False)
        logger.info(f"✓ Document ingested: {document.id}")
        doc_id = document.id
        
        del ingestion_service
        gc.collect()

        logger.info(f"Step 2: Chunking document {doc_id}...")
        chunking_service = ChunkingService(db)
        chunks = chunking_service.chunk_document(document)
        logger.info(f"✓ Created {len(chunks)} chunks for document {doc_id}")
        
        del chunking_service
        del chunks
        gc.collect()

        logger.info(f"Step 3: Generating embeddings for document {doc_id}...")
        logger.info(f"  This may take a few moments depending on the number of chunks...")
        embedding_service = EmbeddingService(db)
        embedding_result = embedding_service.generate_embeddings_for_document(
            document_id=doc_id,
            batch_size=5
        )
        logger.info(f"✓ Embeddings generated: {embedding_result.get('chunks_processed', 0)}/{embedding_result.get('total_chunks', 0)} chunks")
        
        del embedding_service
        gc.collect()

        logger.info(f"Step 4: Syncing embeddings to vector store for document {doc_id}...")
        vector_store = VectorStore(db)
        synced = 0
        batch_size = 50
        batch_num = 0
        while True:
            batch_num += 1
            result = vector_store.sync_embeddings_to_vector(batch_size=batch_size)
            synced += result.get('synced', 0)
            if result.get('synced', 0) > 0:
                logger.info(f"  Batch {batch_num}: Synced {result.get('synced', 0)} embeddings (total: {synced})")
            if result.get('synced', 0) == 0:
                break
            gc.collect()
        
        logger.info(f"✓ Synced {synced} embeddings to vector store for document {doc_id}")
        
        del vector_store
        gc.collect()

        db.refresh(document)
        
        return {
            "success": True,
            "skipped": False,
            "chunks_count": embedding_result.get('total_chunks', 0),
            "embeddings_count": embedding_result.get('chunks_processed', 0),
            "message": f"Successfully processed: {filename}"
        }

    except Exception as e:
        logger.error(f"Failed to process {filename}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        if document:
            try:
                db.expunge(document)
            except:
                pass
        gc.collect()
