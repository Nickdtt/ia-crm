"""
conftest.py - Fixtures compartilhadas para todos os testes.
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.core.database import Base
from app.core.config import settings


# Engine de teste (banco separado ou in-memory)
# Usar credenciais do PostgreSQL Docker (porta 5434, container marketing_crm_db)
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:password@localhost:5434/ia_crm_test"

@pytest_asyncio.fixture
async def db():
    """
    Fixture que cria uma sessão de banco de dados temporária para testes.
    
    - Cria todas as tabelas antes de cada teste
    - Dropa todas as tabelas após cada teste
    - Usa rollback para isolar testes
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool
    )
    
    # Criar tabelas
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Criar sessão
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
    
    # Limpar tabelas após teste
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()
