from fastapi import FastAPI
from database.connection import Base, engine, SessionLocal
from routes.chatbot_route import router as chatbot_router
from core.logging_config import setup_logging, get_logger
from core.pipeline import process_document_pipeline
from database.setup_pgvector import setup_pgvector
import os

setup_logging(level="INFO", log_file="logs/rag_chatbot.log", json_format=False)
logger = get_logger("main")

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="RAG Chatbot API",
    description="Micro-RAG with Guardrails - Challenge Implementation",
    version="1.0.0"
)

app.include_router(chatbot_router)


@app.on_event("startup")
async def startup_event():
    logger.info("=" * 70)
    logger.info("RAG CHATBOT API - Starting Up")
    logger.info("=" * 70)
    logger.info("ENVIRONMENT VARIABLES:")
    logger.info(f"  DATABASE_URL: {os.getenv('DATABASE_URL', 'NOT SET')}")
    logger.info(f"  OPENAI_API_KEY: {'SET' if os.getenv('OPENAI_API_KEY') else 'NOT SET'}")
    logger.info("=" * 70)
    logger.info("✓ Database connection established")
    logger.info("✓ Models synchronized")
    logger.info("=" * 70)
    
    logger.info("Setting up pgvector extension...")
    try:
        setup_pgvector()
        logger.info("✓ pgvector extension configured")
    except Exception as e:
        logger.error(f"✗ Error setting up pgvector: {str(e)}")
        logger.warning("  Continuing anyway, but vector search may not work properly")
    logger.info("=" * 70)
    
    logger.info("Processing documents from data folder...")
    data_folder = "data"
    if os.path.exists(data_folder):
        files = [f for f in os.listdir(data_folder) if f.endswith(('.md', '.txt', '.pdf', '.docx'))]
        if files:
            logger.info(f"Found {len(files)} document(s) to process")
            for i, filename in enumerate(files, 1):
                logger.info(f"[{i}/{len(files)}] Processing: {filename}")
                db = SessionLocal()
                try:
                    result = process_document_pipeline(db, filename)
                    if result.get("success"):
                        if result.get("skipped"):
                            logger.info(f"  ✓ Skipped (already processed)")
                        else:
                            logger.info(f"  ✓ Chunks: {result.get('chunks_count', 0)}")
                            logger.info(f"  ✓ Embeddings: {result.get('embeddings_count', 0)}")
                    else:
                        logger.error(f"  ✗ Error: {result.get('error', 'Unknown')}")
                except Exception as e:
                    logger.error(f"  ✗ Exception processing {filename}: {str(e)}")
                finally:
                    db.close()
                    import gc
                    gc.collect()
            logger.info("=" * 70)
            logger.info("✓ Document processing complete")
        else:
            logger.info("No documents found in data folder")
    else:
        logger.warning(f"Data folder not found: {data_folder}")
    
    logger.info("=" * 70)
    logger.info("API ready for requests")
    logger.info("=" * 70)


@app.get("/")
def root():
    return {
        "message": "RAG Chatbot API - Challenge Implementation",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "ask_question": "POST /chat/ask",
            "metrics": "GET /chat/metrics"
        }
    }


@app.get("/health")
def health_check():
    from database.connection import get_db
    from models.document import Document
    from models.chunk import Chunk
    from sqlalchemy import text
    
    db = next(get_db())
    try:
        total_docs = db.query(Document).count()
        processed_docs = db.query(Document).filter(Document.is_processed == True).count()
        total_chunks = db.query(Chunk).count()
        
        chunks_with_embeddings_query = text("""
            SELECT COUNT(*)
            FROM chunks
            WHERE embedding_vector IS NOT NULL
        """)
        chunks_with_embeddings = db.execute(chunks_with_embeddings_query).scalar() or 0
        
        return {
            "status": "healthy",
            "api": "ready",
            "documents": {
                "total": total_docs,
                "processed": processed_docs,
                "pending": total_docs - processed_docs
            },
            "chunks": {
                "total": total_chunks,
                "with_embeddings": chunks_with_embeddings
            }
        }
    finally:
        db.close()
