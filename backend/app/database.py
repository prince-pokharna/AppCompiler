import os
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text

logger = logging.getLogger("appcompiler")

DATABASE_URL = os.getenv("DATABASE_URL", "")

# Auto-convert postgres:// → postgresql+asyncpg:// and
# postgresql:// → postgresql+asyncpg://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://") and "+asyncpg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Fallback to SQLite for local development when no DATABASE_URL is set
if not DATABASE_URL:
    logger.warning("DATABASE_URL not set — falling back to local SQLite (dev only)")
    DATABASE_URL = "sqlite+aiosqlite:///./appforge_dev.db"

# Engine config differs between PostgreSQL and SQLite
if "sqlite" in DATABASE_URL:
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,       # detect stale connections
        pool_recycle=1800,
    )

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

class Base(DeclarativeBase):
    pass

async def init_db() -> None:
    """Create all tables. Raises a clear error if the DB is unreachable."""
    # Register ORM models before create_all
    import app.models  # noqa: F401

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            # Verify connection is live
            await conn.execute(text("SELECT 1"))
        logger.info(f"Database connected: {DATABASE_URL.split('@')[-1]}")
    except Exception as exc:
        logger.error(
            f"Cannot connect to database.\n"
            f"  URL used: {DATABASE_URL}\n"
            f"  Error: {exc}\n"
            f"  Fix: ensure PostgreSQL is running on port 5432, or set DATABASE_URL in .env"
        )
        raise

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
