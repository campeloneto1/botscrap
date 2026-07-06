import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.config import get_settings
from app.api import auth, profiles, keywords, telegram, dashboard
from app.db.database import engine, Base, async_session
from app.db.models import User
from app.core.security import get_password_hash
from app.core.scheduler import ScrapingScheduler

settings = get_settings()
logger = logging.getLogger(__name__)

# Scheduler instance
scheduler = ScrapingScheduler()

app = FastAPI(
    title=settings.app_name,
    description="Bot de scraping de redes sociais para Telegram",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(profiles.router, prefix="/api/profiles", tags=["profiles"])
app.include_router(keywords.router, prefix="/api/keywords", tags=["keywords"])
app.include_router(telegram.router, prefix="/api/telegram", tags=["telegram"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])


@app.on_event("startup")
async def startup():
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create default admin user
    async with async_session() as db:
        result = await db.execute(select(User).where(User.email == settings.admin_email))
        admin = result.scalar_one_or_none()

        if not admin:
            admin = User(
                email=settings.admin_email,
                hashed_password=get_password_hash(settings.admin_password),
                is_active=True,
                is_admin=True,
            )
            db.add(admin)
            await db.commit()
            logger.info(f"Admin user created: {settings.admin_email}")
        else:
            logger.info(f"Admin user already exists: {settings.admin_email}")

    # Start scheduler
    scheduler.start()
    logger.info("Scheduler started")


@app.on_event("shutdown")
async def shutdown():
    scheduler.stop()
    logger.info("Scheduler stopped")


@app.get("/")
async def root():
    return {"message": "BotScrap API", "docs": "/docs"}


@app.get("/health")
async def health():
    return {"status": "ok"}
