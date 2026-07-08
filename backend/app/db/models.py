from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship

from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=True)
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
    summary = Column(Text, nullable=True)  # AI-generated summary
    media_url = Column(Text, nullable=True)
    ocr_text = Column(Text, nullable=True)  # Text extracted from image via OCR
    has_keyword = Column(Boolean, default=False)
    matched_keywords = Column(JSON, nullable=True)
    status = Column(String(20), default="pending")  # pending, processing, completed, failed
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

    # Relationships
    profile = relationship("Profile")


class AppSettings(Base):
    """Global application settings (singleton - only one row)."""
    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, index=True)

    # Telegram
    telegram_bot_token = Column(String(255), nullable=True)

    # Instagram
    instagram_username = Column(String(255), nullable=True)
    instagram_password = Column(String(255), nullable=True)

    # Twitter/X
    twitter_username = Column(String(255), nullable=True)
    twitter_password = Column(String(255), nullable=True)

    # Facebook
    facebook_email = Column(String(255), nullable=True)
    facebook_password = Column(String(255), nullable=True)

    # Scraping
    scrape_interval_hours = Column(Integer, default=6)
    scrape_delay_seconds = Column(Integer, default=3)

    # Proxies
    use_proxies = Column(Boolean, default=False)
    proxy_list = Column(Text, nullable=True)  # One proxy per line

    # AI Summary
    groq_api_key = Column(String(255), nullable=True)
    enable_ai_summary = Column(Boolean, default=True)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class OCRCache(Base):
    """Cache for OCR results to avoid reprocessing same images."""
    __tablename__ = "ocr_cache"

    id = Column(Integer, primary_key=True, index=True)
    image_url = Column(String(500), unique=True, index=True, nullable=False)
    ocr_text = Column(Text, nullable=True)
    language = Column(String(10), default="por+eng")  # Tesseract language codes
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime, default=datetime.utcnow)
