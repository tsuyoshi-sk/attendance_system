from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .models import Base

class FeliCaRegistration(Base):
    __tablename__ = "felica_registrations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    felica_idm = Column(String(16), unique=True, nullable=False, index=True)  # 8 byte = 16 hex chars
    registered_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relations
    user = relationship("User", back_populates="felica_registrations")