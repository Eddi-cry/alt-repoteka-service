from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session  # <-- добавляем этот импорт
import logging

from ..config import Settings
from ..db.session import init_db, get_db
from .endpoints import package_status, maintainer_pkgs, outdated_pkgs

logger = logging.getLogger(__name__)

# Создаем приложение
app = FastAPI(
    title="ALT Repoteka Service API",
    description="API для отслеживания версий пакетов в ALT Linux",
    version="1.0.0"
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

@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске"""
    settings = Settings()
    init_db(settings)
    logger.info("Database initialized")

@app.get("/health")
async def health_check():
    """Проверка здоровья"""
    return {"status": "ok"}

@app.get("/ready")
async def readiness_check(db: Session = Depends(get_db)):
    """Проверка готовности"""
    try:
        # Проверяем подключение к БД
        db.execute("SELECT 1")
        return {"status": "ready"}
    except Exception as e:
        return {"status": "not ready", "error": str(e)}