from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime

class Audit(Base):
    __tablename__ = "audits"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, index=True)
    title = Column(String)
    description = Column(String)
    keywords = Column(String)  # Przechowywane jako JSON
    created_at = Column(DateTime, default=datetime.utcnow)
    owner_id = Column(Integer, ForeignKey("users.id"))
    status = Column(String, default="pending")
    meta_title = Column(String, nullable=True)
    meta_description = Column(String, nullable=True)
    status_code = Column(Integer, nullable=True)
    audit_data = Column(String, nullable=True)
    suggestions_data = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacje
    user = relationship("User", back_populates="audits")
    pages = relationship("AuditPage", back_populates="audit") 