import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings

# ВАЖНО: Добавь create_tables в импорт!
from ..db.session import create_tables, get_db, init_db
from .endpoints import maintainer_pkgs, outdated_pkgs, package_status

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения (startup и shutdown)."""
    # --- STARTUP ---
    settings = Settings()

    # 1. Инициализация движка (СИНХРОННАЯ операция, await НЕ нужен)
    init_db(settings)

    # 2. Создание таблиц в БД (АСИНХРОННАЯ операция, await НУЖЕН)
    await create_tables()

    logger.info("Database initialized successfully")

    yield  # Приложение работает

    # --- SHUTDOWN ---
    logger.info("Shutting down application")


# Создаем приложение, передавая ему lifespan
app = FastAPI(
    title="ALT Repoteka Service API",
    description="API для отслеживания версий пакетов в ALT Linux",
    version="1.0.0",
    lifespan=lifespan,  # <-- Передаем контекстный менеджер
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
app.include_router(package_status.router)
app.include_router(maintainer_pkgs.router)
app.include_router(outdated_pkgs.router)


@app.get("/health")
async def health_check():
    """Проверка здоровья (без проверки БД, для балансировщика)"""
    return {"status": "ok"}


@app.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """Проверка готовности (с проверкой подключения к БД)"""
    try:
        # Проверяем подключение к БД с async запросом
        await db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return {"status": "not ready", "error": str(e)}
