"""
Teste manual do clientService com novos campos.

Valida:
- create_client com first_name, last_name, segment, monthly_budget, main_marketing_problem
- get_client_by_id
- get_client_by_phone
- update_client com novos campos
- list_clients
- delete_client
- Validação de telefone único
"""
import asyncio
from decimal import Decimal
from app.core.database import AsyncSessionLocal
from app.services.clientService import (
    create_client,
    get_client_by_id,
    get_client_by_phone,
    update_client,
    list_clients,
    delete_client
)
from app.schemas.clientSchema import ClientCreate, ClientUpdate
from app.models.client import ClientSegment


async def test_client_service():
    """Testa todas as operações do clientService"""
    
    async with AsyncSessionLocal() as db:
        print("=" * 60)
        print("TESTE 1: Criar cliente com todos os campos novos")
        print("=" * 60)
        
        try:
            client_data = ClientCreate(
                first_name="João",
                last_name="Silva",
                phone="11999887766",
                email="joao.silva@empresa.com",
                company_name="Silva Odontologia",
                segment=ClientSegment.CLINICA_ODONTOLOGICA,
                monthly_budget=Decimal("8000.00"),
                main_marketing_problem="Pouca presença digital, não aparece no Google",
                notes="Lead qualificado via Instagram"
            )
            
            client = await create_client(client_data, db)
            
            print(f"✅ Cliente criado com sucesso!")
            print(f"   ID: {client.id}")
            print(f"   Nome completo: {client.full_name}")
            print(f"   Telefone: {client.phone}")
            print(f"   Email: {client.email}")
            print(f"   Empresa: {client.company_name}")
            print(f"   Segmento: {client.segment.value}")
            print(f"   Orçamento mensal: R$ {client.monthly_budget}")
            print(f"   Problema principal: {client.main_marketing_problem}")
            print()
            
            client_id = client.id
            
        except Exception as e:
            print(f"❌ Erro ao criar cliente: {e}")
            return
        
        # ============================================
        print("=" * 60)
        print("TESTE 2: Buscar cliente por ID")
        print("=" * 60)
        
        found = await get_client_by_id(client_id, db)
        if found:
            print(f"✅ Cliente encontrado: {found.full_name}")
            print(f"   Segmento: {found.segment.value}")
            print(f"   Orçamento: R$ {found.monthly_budget}")
        else:
            print("❌ Cliente não encontrado")
        print()
        
        # ============================================
        print("=" * 60)
        print("TESTE 3: Buscar cliente por telefone")
        print("=" * 60)
        
        found_by_phone = await get_client_by_phone(db, "11999887766")
        if found_by_phone:
            print(f"✅ Cliente encontrado pelo telefone: {found_by_phone.full_name}")
            print(f"   Email: {found_by_phone.email}")
        else:
            print("❌ Cliente não encontrado pelo telefone")
        print()
        
        # ============================================
        print("=" * 60)
        print("TESTE 4: Atualizar cliente (novos campos)")
        print("=" * 60)
        
        try:
            update_data = ClientUpdate(
                first_name="João Carlos",
                monthly_budget=Decimal("12000.00"),
                main_marketing_problem="Precisa aumentar conversão de leads",
                notes="Cliente aumentou orçamento após primeira reunião"
            )
            
            updated = await update_client(client_id, update_data, db)
            
            print(f"✅ Cliente atualizado com sucesso!")
            print(f"   Nome atualizado: {updated.full_name}")
            print(f"   Novo orçamento: R$ {updated.monthly_budget}")
            print(f"   Novo problema: {updated.main_marketing_problem}")
            print(f"   Notas: {updated.notes}")
        except Exception as e:
            print(f"❌ Erro ao atualizar: {e}")
        print()
        
        # ============================================
        print("=" * 60)
        print("TESTE 5: Criar segundo cliente (segmento diferente)")
        print("=" * 60)
        
        try:
            client2_data = ClientCreate(
                first_name="Maria",
                last_name="Santos",
                phone="11988776655",
                email="maria@clinica.com",
                segment=ClientSegment.CLINICA_MEDICA,
                monthly_budget=Decimal("15000.00"),
                main_marketing_problem="Atrair mais pacientes particulares"
            )
            
            client2 = await create_client(client2_data, db)
            print(f"✅ Segundo cliente criado: {client2.full_name}")
            print(f"   Segmento: {client2.segment.value}")
            print(f"   Orçamento: R$ {client2.monthly_budget}")
            
            client2_id = client2.id
        except Exception as e:
            print(f"❌ Erro ao criar segundo cliente: {e}")
            client2_id = None
        print()
        
        # ============================================
        print("=" * 60)
        print("TESTE 6: Listar todos os clientes")
        print("=" * 60)
        
        all_clients = await list_clients(db)
        print(f"✅ Total de clientes: {len(all_clients)}")
        for idx, c in enumerate(all_clients, 1):
            print(f"   {idx}. {c.full_name} - {c.segment.value} - R$ {c.monthly_budget}/mês")
        print()
        
        # ============================================
        print("=" * 60)
        print("TESTE 7: Validar telefone único (deve falhar)")
        print("=" * 60)
        
        try:
            duplicate = ClientCreate(
                first_name="Pedro",
                last_name="Oliveira",
                phone="11999887766",  # ❌ Telefone duplicado
                email="pedro@email.com",
                segment=ClientSegment.DENTISTA_AUTONOMO,
                monthly_budget=Decimal("5000.00"),
                main_marketing_problem="Problema qualquer"
            )
            
            await create_client(duplicate, db)
            print("❌ ERRO: Deveria ter bloqueado telefone duplicado!")
        except ValueError as e:
            print(f"✅ Validação funcionou: {e}")
        print()
        
        # ============================================
        print("=" * 60)
        print("TESTE 8: Deletar clientes")
        print("=" * 60)
        
        deleted1 = await delete_client(client_id, db)
        print(f"✅ Cliente 1 deletado: {deleted1}")
        
        if client2_id:
            deleted2 = await delete_client(client2_id, db)
            print(f"✅ Cliente 2 deletado: {deleted2}")
        
        print()
        print("=" * 60)
        print("✅ TODOS OS TESTES CONCLUÍDOS!")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_client_service())
