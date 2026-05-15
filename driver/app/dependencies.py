import os
from typing import Optional, AsyncGenerator
from pydantic_settings import BaseSettings
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

class Settings(BaseSettings):
    # Configuración de Base de Datos
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql+asyncpg://orchestrator:orchestrator@postgres:5432/orchestrator_db"
    )

    # Configuración del Driver
    SSH_ENABLED: bool = os.getenv("SSH_ENABLED", "false").lower() == "true"
    SSH_USER: str = os.getenv("SSH_USER", "root")
    SSH_KEY_PATH: str = os.getenv("SSH_KEY_PATH", "/root/.ssh/id_rsa")
    SSH_PASSWORD: Optional[str] = os.getenv("SSH_PASSWORD")
    
    # Rutas y Cluster
    BASE_IMAGE_PATH: str = os.getenv("BASE_IMAGE_PATH", "/mnt/storage/base/")
    CLUSTER_TYPE: str = os.getenv("CLUSTER_TYPE", "linux")

    class Config:
        env_file = ".env"

# Instancia global
settings = Settings()

# Motor de BD Asíncrono
engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)

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