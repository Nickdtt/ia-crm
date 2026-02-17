"""
Script para criar banco de teste ia_crm_test
"""
import asyncio
import asyncpg

async def create_test_database():
    """Cria banco de teste se não existir."""
    try:
        # Conectar ao banco padrão (marketing_crm) usando credenciais corretas
        conn = await asyncpg.connect(
            host='localhost',
            port=5434,
            user='postgres',
            password='password',
            database='marketing_crm'
        )
        
        # Verificar se banco já existe
        result = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = 'ia_crm_test'"
        )
        
        if result:
            print("✅ Banco 'ia_crm_test' já existe")
        else:
            # Criar banco de teste
            await conn.execute('CREATE DATABASE ia_crm_test')
            print("✅ Banco 'ia_crm_test' criado com sucesso!")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    asyncio.run(create_test_database())
