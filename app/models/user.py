from enum import Enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.core.database import Base
import json

class UserRole(str, Enum):
    GUEST = "guest"
    USER = "user"
    PREMIUM = "premium"
    ADMIN = "admin"

class SubscriptionTier(str, Enum):
    FREE = "free"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    role = Column(SQLEnum(UserRole), default=UserRole.USER)
    subscription_tier = Column(SQLEnum(SubscriptionTier), default=SubscriptionTier.FREE)
    subscription_end = Column(DateTime, nullable=True)
    permissions = Column(String, default=json.dumps(["read_audit"]))
    activation_token = Column(String, nullable=True)
    login_attempts = Column(Integer, default=0)
    last_login_attempt = Column(DateTime, nullable=True)
    blocked_until = Column(DateTime, nullable=True)

    # Relacje
    audits = relationship("Audit", back_populates="user")

    def get_permissions(self):
        base_permissions = {
            UserRole.GUEST: ["read_public"],
            UserRole.USER: ["read_public", "read_audit", "create_basic_audit"],
            UserRole.PREMIUM: ["read_public", "read_audit", "create_audit", 
                             "analyze_audit", "export_report", "ai_suggestions"],
            UserRole.ADMIN: ["read_public", "read_audit", "create_audit", 
                           "analyze_audit", "export_report", "ai_suggestions", 
                           "manage_users"]
        }
        return base_permissions.get(self.role, [])

    def is_subscription_active(self) -> bool:
        if self.subscription_tier == SubscriptionTier.FREE:
            return True
        return bool(self.subscription_end and self.subscription_end > datetime.utcnow()) 