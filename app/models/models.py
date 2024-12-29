from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from .database import Base
from typing import Any

class Audit(Base):
    __tablename__ = "audits"
    __table_args__ = (
        Index('idx_audit_status_created', 'status', 'created_at'),
        Index('idx_audit_url', 'url'),
    )

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, index=True)
    status = Column(String, default="pending")  # pending, in_progress, done, error
    meta_title = Column(String, nullable=True)
    meta_description = Column(String, nullable=True)
    status_code = Column(Integer, nullable=True)
    audit_data = Column(Text, nullable=True)
    suggestions_data = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # rekurencyjny crawler – relacja do AuditPage
    pages = relationship("AuditPage", back_populates="audit", cascade="all, delete-orphan")

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

class AuditPage(Base):
    __tablename__ = "audit_pages"

    id = Column(Integer, primary_key=True, index=True)
    audit_id = Column(Integer, ForeignKey("audits.id", ondelete="CASCADE"))
    url = Column(String, index=True)
    status_code = Column(Integer)
    visited = Column(Boolean, default=False)

    page_data = Column(JSONB)  # linki, meta, headings, itp.

    # relacja do Audit
    audit = relationship("Audit", back_populates="pages")

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
