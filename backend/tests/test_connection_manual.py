"""
Script manual para testar conexão com o banco marketing_crm.

Execute: python test_connection_manual.py
"""
import asyncio
import sys
from pathlib import Path

# Adicionar o diretório pai ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.core.database import AsyncSessionLocal


async def test_connection():
    """Testa conexão básica com o banco"""
    print("\n🔍 Testando conexão com banco...")
    
    async with AsyncSessionLocal() as session:
        # Teste 1: SELECT básico
        result = await session.execute(text("SELECT 1"))
        assert result.scalar() == 1
        print("✅ Conexão funcionando")
        
        # Teste 2: Nome do banco
        result = await session.execute(text("SELECT current_database()"))
        db_name = result.scalar()
        print(f"✅ Banco conectado: {db_name}")
        assert db_name == "marketing_crm", f"❌ Esperado 'marketing_crm', got '{db_name}'"
        
        # Teste 3: Listar tabelas
        query = text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        result = await session.execute(query)
        tables = [row[0] for row in result.fetchall()]
        print(f"✅ Tabelas encontradas: {tables}")
        
        # Teste 4: Verificar tabelas esperadas
        expected = ['alembic_version', 'appointments', 'clients', 'conversations', 'messages', 'users']
        for table in expected:
            assert table in tables, f"❌ Tabela '{table}' não encontrada"
        print("✅ Todas as tabelas necessárias existem")
        
        print("\n✅ TODOS OS TESTES DE CONEXÃO PASSARAM!\n")


if __name__ == "__main__":
    asyncio.run(test_connection())
