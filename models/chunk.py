from sqlalchemy import Column, Integer, String, Text, ForeignKey, Float
from sqlalchemy.orm import relationship
from database import Base

class Chunk(Base):

    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)

    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)

    chunk_size = Column(Integer, nullable=False)
    token_count = Column(Integer, nullable=True)

    previous_chunk_id = Column(Integer, nullable=True)
    next_chunk_id = Column(Integer, nullable=True)

    embedding = Column(Text, nullable=True)
    embedding_model = Column(String(100), nullable=True)

    section_title = Column(String(500), nullable=True)

    document = relationship("Document", backref="chunks")

    def __repr__(self):
        return f"<Chunk(id={self.id}, doc_id={self.document_id}, index={self.chunk_index})>"
