from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.sql import func
from database import Base

class Document(Base):

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_path = Column(String(500), nullable=False)

    content = Column(Text, nullable=False)
    content_preview = Column(String(500))

    num_pages = Column(Integer, nullable=True)
    num_words = Column(Integer, nullable=False)
    num_characters = Column(Integer, nullable=False)
    language = Column(String(10), nullable=True)

    is_processed = Column(Boolean, default=False)
    processing_status = Column(String(50), default="uploaded")
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<Document(id={self.id}, filename={self.filename}, type={self.file_type})>"
