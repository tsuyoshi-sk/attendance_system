from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    employee_id = Column(String(50), unique=True, nullable=False, index=True)
    department = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relations
    suica_registrations = relationship("SuicaRegistration", back_populates="user")
    felica_registrations = relationship("FeliCaRegistration", back_populates="user")
    attendance_records = relationship("AttendanceRecord", back_populates="user")

class SuicaRegistration(Base):
    __tablename__ = "suica_registrations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    suica_idm_hash = Column(String(64), unique=True, nullable=False, index=True)
    registered_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relations
    user = relationship("User", back_populates="suica_registrations")

class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    type = Column(String(20), nullable=False)  # check_in, check_out
    location = Column(String(100), default="office")
    suica_idm_hash = Column(String(64), index=True)
    felica_idm = Column(String(16), index=True)  # FeliCa IDM
    session_id = Column(String(100))
    
    # Relations
    user = relationship("User", back_populates="attendance_records")