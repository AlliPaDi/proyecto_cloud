import os
from typing import Optional, AsyncGenerator
from pydantic_settings import BaseSettings
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

class Settings(BaseSettings):
    # Configuración de Base de Datos
    DATABASE_URL: str = "postgresql+asyncpg://orchestrator:orchestrator@postgres:5432/orchestrator_db"

    # Configuración del Driver
    SSH_ENABLED: bool = False
    SSH_USER: str = "root"
    SSH_KEY_PATH: str = "/root/.ssh/id_rsa"
    SSH_PASSWORD: Optional[str] = None

    # Rutas y Cluster
    BASE_IMAGE_PATH: str = "/mnt/storage/base/"
    CLUSTER_TYPE: str = "linux"

    class Config:
        env_file = ".env"

# Instancia global
settings = Settings()

# Motor de BD Asíncrono
engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()