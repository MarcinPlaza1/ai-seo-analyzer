from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.core import Base
from datetime import datetime

class AuditPage(Base):
    __tablename__ = "audit_pages"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, index=True)
    title = Column(String)
    content = Column(String)
    status_code = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    audit_id = Column(Integer, ForeignKey("audits.id"))

    # Relacje
    audit = relationship("Audit", back_populates="pages") 