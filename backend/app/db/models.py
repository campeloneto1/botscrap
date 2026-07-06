from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship

from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    profiles = relationship("Profile", back_populates="user", cascade="all, delete-orphan")
    keywords = relationship("Keyword", back_populates="user", cascade="all, delete-orphan")
    telegram_groups = relationship("TelegramGroup", back_populates="user", cascade="all, delete-orphan")


class TelegramGroup(Base):
    __tablename__ = "telegram_groups"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    chat_id = Column(String(100), nullable=False)
    name = Column(String(255), nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="telegram_groups")
    profiles = relationship("Profile", back_populates="telegram_group")


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    telegram_group_id = Column(Integer, ForeignKey("telegram_groups.id"), nullable=True)
    platform = Column(String(50), nullable=False)  # instagram, twitter, etc
    username = Column(String(255), nullable=False)
    active = Column(Boolean, default=True)
    last_scraped = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="profiles")
    telegram_group = relationship("TelegramGroup", back_populates="profiles")
    posts = relationship("ProcessedPost", back_populates="profile", cascade="all, delete-orphan")


class ProcessedPost(Base):
    __tablename__ = "processed_posts"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    post_id = Column(String(255), nullable=False)  # ID único da rede social
    content = Column(Text, nullable=True)
    media_url = Column(Text, nullable=True)
    has_keyword = Column(Boolean, default=False)
    matched_keywords = Column(JSON, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    processed_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    profile = relationship("Profile", back_populates="posts")


class Keyword(Base):
    __tablename__ = "keywords"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    word = Column(String(255), nullable=False)
    priority = Column(Integer, default=1)  # 1=normal, 2=importante, 3=urgente
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="keywords")


class ScrapingLog(Base):
    __tablename__ = "scraping_logs"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(50), nullable=False)  # success, error, skipped
    message = Column(Text, nullable=True)
    posts_found = Column(Integer, default=0)
    posts_sent = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
