"""
src/db/postgres.py

SQLAlchemy models + session management for the people/embeddings/logs/jobs tables.
Schema is defined in configs/schema.sql -- these models mirror that schema so we
get a clean Python interface without hand-writing raw SQL everywhere.
"""

import os
from datetime import datetime

from sqlalchemy import create_engine, Column, Integer, String, Float, Text, ForeignKey, ARRAY, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://safeguard:safeguard_dev_pw@localhost:5432/safeguardai")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class Person(Base):
    __tablename__ = "people"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    employee_id = Column(String(100), unique=True)
    role = Column(String(255))
    department = Column(String(255))
    notes = Column(Text)
    photo_path = Column(String(500))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    embeddings = relationship("Embedding", back_populates="person", cascade="all, delete-orphan")
    logs = relationship("RecognitionLog", back_populates="person")


class Embedding(Base):
    __tablename__ = "embeddings"

    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey("people.id", ondelete="CASCADE"), nullable=False)
    faiss_index_id = Column(Integer, unique=True, nullable=False)
    embedding = Column(ARRAY(Float), nullable=False)
    source_photo = Column(String(500))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    person = relationship("Person", back_populates="embeddings")


class RecognitionLog(Base):
    __tablename__ = "recognition_logs"

    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey("people.id", ondelete="SET NULL"), nullable=True)
    source = Column(String(255), nullable=False)
    timestamp_in_video = Column(Float, nullable=True)
    confidence = Column(Float, nullable=False)
    status = Column(String(20), nullable=False, default="unknown")  # known | unknown | spoof
    thumbnail_path = Column(String(500))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    person = relationship("Person", back_populates="logs")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True)
    filename = Column(String(500), nullable=False)
    status = Column(String(20), nullable=False, default="queued")  # queued | processing | done | failed
    progress = Column(Float, nullable=False, default=0.0)
    error_message = Column(Text)
    result_path = Column(String(500))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow)


def get_session():
    """Use as: with get_session() as session: ..."""
    return SessionLocal()


def init_db():
    """Creates all tables if they don't exist. Safe to call multiple times."""
    Base.metadata.create_all(engine)