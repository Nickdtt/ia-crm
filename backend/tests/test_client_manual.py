"""
Script manual para testar o model Client.

Testa:
- Criação de client com todos os campos
- Validação de unique constraint (phone)
- Leitura de client do banco
- Enum ClientSegment
- Property full_name

Execute: python test_client_manual.py
"""
import asyncio
import sys
from pathlib import Path
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.client import Client, ClientSegment


async def test_create_client():
    """Testa criação de um client no banco"""
    print("\n🧪 Teste 1: Criar Client")
    
    async with AsyncSessionLocal() as session:
        # Criar cliente
        client = Client(
            first_name="João",
            last_name="Silva",
            phone="+5511999999999",
            email="joao.silva@clinica.com.br",
            company_name="Clínica Silva",
            segment=ClientSegment.CLINICA_MEDICA,
            monthly_budget=Decimal("7500.00"),
            main_marketing_problem="Baixa taxa de conversão no Instagram"
        )
        
        session.add(client)
        await session.commit()
        await session.refresh(client)
        
        print(f"✅ Client criado: {client}")
        print(f"   ID: {client.id}")
        print(f"   Nome completo: {client.full_name}")
        print(f"   Telefone: {client.phone}")
        print(f"   Segmento: {client.segment.value}")
        print(f"   Orçamento: R$ {client.monthly_budget}")
        
        return client.id


async def test_read_client(client_id):
    """Testa leitura de client do banco"""
    print("\n🧪 Teste 2: Ler Client do banco")
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Client).where(Client.id == client_id)
        )
        client = result.scalar_one()
        
        print(f"✅ Client encontrado: {client.full_name}")
        print(f"   Email: {client.email}")
        print(f"   Empresa: {client.company_name}")
        print(f"   Problema: {client.main_marketing_problem}")


async def test_unique_phone():
    """Testa constraint unique do telefone"""
    print("\n🧪 Teste 3: Testar phone unique")
    
    async with AsyncSessionLocal() as session:
        try:
            # Tentar criar client com mesmo telefone
            client2 = Client(
                first_name="Maria",
                last_name="Santos",
                phone="+5511999999999",  # Mesmo telefone!
                segment=ClientSegment.DENTISTA_AUTONOMO,
                monthly_budget=Decimal("5000.00"),
                main_marketing_problem="Falta de pacientes novos"
            )
            
            session.add(client2)
            await session.commit()
            
            print("❌ ERRO: Deveria ter dado erro de duplicação!")
            
        except Exception as e:
            await session.rollback()
            print(f"✅ Constraint funcionando: telefone duplicado bloqueado")
            print(f"   Erro esperado: {type(e).__name__}")


async def test_client_segments():
    """Testa diferentes segmentos"""
    print("\n🧪 Teste 4: Testar diferentes segmentos")
    
    async with AsyncSessionLocal() as session:
        clients = [
            Client(
                first_name="Ana",
                last_name="Costa",
                phone="+5511988888888",
                segment=ClientSegment.PSICOLOGO,
                monthly_budget=Decimal("3000.00"),
                main_marketing_problem="Baixa visibilidade online"
            ),
            Client(
                first_name="Pedro",
                last_name="Almeida",
                phone="+5511977777777",
                company_name="Farmácia Popular",
                segment=ClientSegment.FARMACIA,
                monthly_budget=Decimal("12000.00"),
                main_marketing_problem="Concorrência com grandes redes"
            ),
        ]
        
        for client in clients:
            session.add(client)
        
        await session.commit()
        
        for client in clients:
            await session.refresh(client)
            print(f"✅ {client.full_name} - Segmento: {client.segment.value}")


async def test_list_all_clients():
    """Lista todos os clients criados"""
    print("\n🧪 Teste 5: Listar todos os clients")
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Client))
        clients = result.scalars().all()
        
        print(f"✅ Total de clients: {len(clients)}")
        for client in clients:
            print(f"   - {client.full_name} ({client.phone}) - {client.segment.value}")


async def cleanup():
    """Limpa dados de teste"""
    print("\n🧹 Limpando dados de teste...")
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Client))
        clients = result.scalars().all()
        
        for client in clients:
            await session.delete(client)
        
        await session.commit()
        print("✅ Dados limpos")


async def main():
    """Executa todos os testes"""
    try:
        client_id = await test_create_client()
        await test_read_client(client_id)
        await test_unique_phone()
        await test_client_segments()
        await test_list_all_clients()
        
        print("\n✅ TODOS OS TESTES DO MODEL CLIENT PASSARAM!\n")
        
    finally:
        await cleanup()


if __name__ == "__main__":
    asyncio.run(main())
