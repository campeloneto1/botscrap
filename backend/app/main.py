import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.config import get_settings
from app.api import auth, profiles, keywords, telegram, dashboard, users
from app.api import settings as settings_api
from app.api.settings import set_scheduler as set_settings_scheduler
from app.db.database import engine, Base, async_session
from app.db.models import User
from app.core.security import get_password_hash
from app.core.scheduler import ScrapingScheduler

settings = get_settings()
logger = logging.getLogger(__name__)

# Scheduler instance
scheduler = ScrapingScheduler()

# Share scheduler with APIs
dashboard.set_scheduler(scheduler)
set_settings_scheduler(scheduler)

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
app.include_router(settings_api.router, prefix="/api/settings", tags=["settings"])
app.include_router(users.router, prefix="/api/users", tags=["users"])


@app.on_event("startup")
async def startup():
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create default admin user
    async with async_session() as db:
        # Verifica por username OU email para evitar duplicatas
        result = await db.execute(
            select(User).where(
                (User.username == "admin") | (User.email == settings.admin_email)
            )
        )
        admin = result.scalar_one_or_none()

        if not admin:
            admin = User(
                username="admin",
                email=settings.admin_email,
                hashed_password=get_password_hash(settings.admin_password),
                is_active=True,
                is_admin=True,
            )
            db.add(admin)
            await db.commit()
            logger.info("Admin user created: admin")
        else:
            # Garante que o usuário existente é admin
            if not admin.is_admin:
                admin.is_admin = True
                await db.commit()
                logger.info(f"User '{admin.username}' promoted to admin")
            else:
                logger.info(f"Admin user already exists: {admin.username}")

    # Start scheduler and load settings from database
    scheduler.start()
    await scheduler.init_from_db()
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
