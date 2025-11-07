import re
from typing import List, Dict, Optional
from sqlalchemy.orm import Session

from models.document import Document
from models.chunk import Chunk
from core.config import settings

class ChunkingService:

    def __init__(self, db: Session):
        self.db = db
        self.chunk_size = settings.CHUNK_SIZE
        self.chunk_overlap = settings.CHUNK_OVERLAP

    def chunk_document(self, document: Document) -> List[Chunk]:
        from core.logging_config import get_logger
        logger = get_logger("chunking")
        
        content = str(document.content)
        logger.debug(f"Chunking document {document.id}: {len(content)} characters")

        deleted_count = self.db.query(Chunk).filter(Chunk.document_id == document.id).delete()
        if deleted_count > 0:
            logger.debug(f"Deleted {deleted_count} existing chunks")
        self.db.commit()

        logger.debug(f"Creating chunks with size={self.chunk_size}, overlap={self.chunk_overlap}")
        chunks_data = self._create_chunks_with_overlap(content)
        logger.info(f"Created {len(chunks_data)} chunks from document {document.id}")

        if not chunks_data:
            logger.warning(f"No chunks created for document {document.id}")
            return []

        chunks = []
        previous_chunk = None

        for idx, chunk_text in enumerate(chunks_data):
            chunk = Chunk(
                document_id=document.id,
                content=chunk_text,
                chunk_index=idx,
                chunk_size=len(chunk_text),
                token_count=self._estimate_tokens(chunk_text),
                section_title=self._extract_section_title(chunk_text),
                previous_chunk_id=previous_chunk.id if previous_chunk else None
            )

            self.db.add(chunk)
            self.db.flush()

            if previous_chunk:
                previous_chunk.next_chunk_id = chunk.id

            chunks.append(chunk)
            previous_chunk = chunk

        self.db.commit()
        logger.debug(f"Saved {len(chunks)} chunks to database")

        setattr(document, "is_processed", False)
        setattr(document, "processing_status", "chunked")
        self.db.commit()

        return chunks

    def _create_chunks_with_overlap(self, text: str) -> List[str]:
        """
        Create chunks with overlap, trying to break at paragraph or line boundaries.
        """
        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = start + self.chunk_size

            if end < text_length:
                search_start = max(end - 100, start)
                search_end = min(end + 100, text_length)

                paragraph_break = text.find('\n\n', search_start, search_end)

                if paragraph_break != -1 and paragraph_break > start:
                    end = paragraph_break + 2
                else:
                    line_break = text.find('\n', max(end - 50, start), min(end + 50, text_length))
                    if line_break != -1 and line_break > start:
                        end = line_break + 1
            else:
                end = text_length

            chunk_text = text[start:end].strip()

            if chunk_text:
                chunks.append(chunk_text)

            new_start = end - self.chunk_overlap
            
            if new_start <= start:
                new_start = start + 1
            
            if new_start >= text_length:
                break
                
            start = new_start

        return chunks

    def _estimate_tokens(self, text: str) -> int:

        return len(text) // 4

    def _extract_section_title(self, text: str) -> Optional[str]:
        lines = text.split('\n')
        for line in lines[:3]:
            if line.strip().startswith('#'):
                return line.strip().lstrip('#').strip()
        return None

    def get_chunks_by_document(self, document_id: int) -> List[Chunk]:

        return self.db.query(Chunk).filter(
            Chunk.document_id == document_id
        ).order_by(Chunk.chunk_index).all()

    def get_chunk_with_context(self, chunk_id: int, context_size: int = 1) -> Dict:

        chunk = self.db.query(Chunk).filter(Chunk.id == chunk_id).first()
        if not chunk:
            return {}

        previous_chunks = []
        next_chunks = []

        current = chunk
        for _ in range(context_size):
            prev_id = current.previous_chunk_id
            if prev_id is not None:
                prev = self.db.query(Chunk).filter(
                    Chunk.id == prev_id
                ).first()
                if prev:
                    previous_chunks.insert(0, prev)
                    current = prev
            else:
                break

        current = chunk
        for _ in range(context_size):
            next_id = current.next_chunk_id
            if next_id is not None:
                nxt = self.db.query(Chunk).filter(
                    Chunk.id == next_id
                ).first()
                if nxt:
                    next_chunks.append(nxt)
                    current = nxt
            else:
                break

        return {
            'chunk': chunk,
            'previous': previous_chunks,
            'next': next_chunks,
            'full_context': ''.join([c.content for c in previous_chunks]) +
                           chunk.content +
                           ''.join([c.content for c in next_chunks])
        }

    def get_stats(self) -> Dict:

        total_chunks = self.db.query(Chunk).count()
        avg_chunk_size = self.db.query(
            func.avg(Chunk.chunk_size)
        ).scalar() or 0

        return {
            'total_chunks': total_chunks,
            'avg_chunk_size': round(avg_chunk_size, 2),
            'avg_token_estimate': round(avg_chunk_size / 4, 2),
            'chunk_size_configured': self.chunk_size,
            'overlap_configured': self.chunk_overlap
        }

from sqlalchemy import func
