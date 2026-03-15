"""
Script de teste para validar memória persistente do agente.

CENÁRIOS TESTADOS:
1. Cliente retornando COM appointment → Atendimento VIP
2. Cliente retornando SEM appointment → Requalificação

SETUP:
- Cria cliente no banco
- Cria appointment (cenário 1)
- Simula mensagem do WhatsApp
- Valida reconhecimento e mensagens personalizadas
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from uuid import uuid4
from decimal import Decimal

# Adicionar backend ao path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.core.database import AsyncSessionLocal
from app.models.client import Client
from app.models.appointment import Appointment, AppointmentStatus
from app.schemas.clientSchema import ClientSegment
from app.api.whatsappControllers import carregar_state_do_usuario
from zoneinfo import ZoneInfo

BRAZIL_TZ = ZoneInfo("America/Sao_Paulo")


async def criar_cliente_teste(with_appointment: bool = False):
    """
    Cria cliente de teste no banco.
    
    Args:
        with_appointment: Se True, cria appointment junto
        
    Returns:
        tuple: (client_id, appointment_id ou None)
    """
    async with AsyncSessionLocal() as db:
        # Cliente de teste
        client = Client(
            id=uuid4(),
            first_name="Maria",
            last_name="Silva",
            phone="71999888777",  # Telefone único para teste
            email="maria.silva@testecrm.com",
            company_name="Silva Odontologia",
            segment=ClientSegment.CLINICA_ODONTOLOGICA,
            monthly_budget=Decimal("8000.00"),
            main_marketing_problem="Baixa conversão de leads do Google Ads"
        )
        db.add(client)
        await db.flush()
        
        appointment_id = None
        if with_appointment:
            # Criar appointment para amanhã às 14h
            tomorrow_14h = datetime.now(BRAZIL_TZ).replace(
                hour=14, minute=0, second=0, microsecond=0
            ) + timedelta(days=1)
            
            appointment = Appointment(
                id=uuid4(),
                client_id=client.id,
                scheduled_at=tomorrow_14h,
                duration_minutes=30,
                meeting_type="CONSULTORIA_INICIAL",
                status=AppointmentStatus.PENDING
            )
            db.add(appointment)
            await db.flush()
            appointment_id = appointment.id
        
        await db.commit()
        
        return str(client.id), str(appointment_id) if appointment_id else None


async def limpar_cliente_teste(phone: str):
    """Remove cliente de teste e seus appointments."""
    from sqlalchemy import delete
    
    async with AsyncSessionLocal() as db:
        # Buscar cliente pelo telefone
        from app.services.clientService import get_client_by_phone
        client = await get_client_by_phone(db, phone)
        
        if client:
            # Deletar appointments
            await db.execute(
                delete(Appointment).where(Appointment.client_id == client.id)
            )
            
            # Deletar cliente
            await db.execute(
                delete(Client).where(Client.id == client.id)
            )
            
            await db.commit()
            print(f"✅ Cliente {phone} removido do banco")


async def test_cenario_1_com_appointment():
    """
    CENÁRIO 1: Cliente retornando COM appointment.
    
    Espera-se:
    - conversation_mode = "returning_with_appointment"
    - Estado com client_id e appointment_id populados
    - qualification_complete = True
    - budget_qualified = True
    """
    print("=" * 80)
    print("TESTE 1: Cliente retornando COM appointment")
    print("=" * 80)
    
    # 1. Criar cliente com appointment
    print("\n📝 SETUP: Criando cliente com appointment...")
    client_id, appointment_id = await criar_cliente_teste(with_appointment=True)
    print(f"   ✅ Cliente criado: {client_id}")
    print(f"   ✅ Appointment criado: {appointment_id}")
    
    try:
        # 2. Simular carregamento de estado (como whatsappControllers faz)
        print("\n🔍 TESTE: Carregando estado do cliente...")
        remote_jid = "5571999888777@s.whatsapp.net"  # Simula WhatsApp ID
        phone = "71999888777"
        
        state = await carregar_state_do_usuario(remote_jid, phone)
        
        # 3. Validar estado retornado
        print("\n📊 RESULTADO:")
        print(f"   conversation_mode: {state.get('conversation_mode')}")
        print(f"   client_id: {state.get('client_id')}")
        print(f"   appointment_id: {state.get('appointment_id')}")
        print(f"   qualification_complete: {state.get('qualification_complete')}")
        print(f"   budget_qualified: {state.get('budget_qualified')}")
        print(f"   client_data: {state.get('client_data', {}).get('first_name')}")
        
        # 4. Assertions
        assertions = []
        
        if state.get("conversation_mode") == "returning_with_appointment":
            assertions.append("✅ conversation_mode correto (returning_with_appointment)")
        else:
            assertions.append(f"❌ conversation_mode esperado: returning_with_appointment, recebido: {state.get('conversation_mode')}")
        
        if state.get("client_id") == client_id:
            assertions.append("✅ client_id carregado corretamente")
        else:
            assertions.append("❌ client_id não corresponde")
        
        if state.get("appointment_id") == appointment_id:
            assertions.append("✅ appointment_id carregado corretamente")
        else:
            assertions.append("❌ appointment_id não corresponde")
        
        if state.get("qualification_complete") is True:
            assertions.append("✅ qualification_complete = True")
        else:
            assertions.append("❌ qualification_complete deveria ser True")
        
        if state.get("budget_qualified") is True:
            assertions.append("✅ budget_qualified = True (R$ 8.000 >= R$ 3.000)")
        else:
            assertions.append("❌ budget_qualified deveria ser True")
        
        print("\n" + "\n   ".join(assertions))
        
    finally:
        # 5. Cleanup
        print("\n🧹 CLEANUP: Removendo dados de teste...")
        await limpar_cliente_teste("71999888777")


async def test_cenario_2_sem_appointment():
    """
    CENÁRIO 2: Cliente retornando SEM appointment.
    
    Espera-se:
    - conversation_mode = "returning_without_appointment"
    - Estado com client_id populado mas sem appointment_id
    - qualification_complete = False (precisa revalidar)
    - budget_qualified = True (baseado em dados antigos)
    """
    print("\n" + "=" * 80)
    print("TESTE 2: Cliente retornando SEM appointment")
    print("=" * 80)
    
    # 1. Criar cliente SEM appointment
    print("\n📝 SETUP: Criando cliente sem appointment...")
    client_id, _ = await criar_cliente_teste(with_appointment=False)
    print(f"   ✅ Cliente criado: {client_id}")
    print(f"   ℹ️  Nenhum appointment criado")
    
    try:
        # 2. Simular carregamento de estado
        print("\n🔍 TESTE: Carregando estado do cliente...")
        remote_jid = "5571999888777@s.whatsapp.net"
        phone = "71999888777"
        
        state = await carregar_state_do_usuario(remote_jid, phone)
        
        # 3. Validar estado retornado
        print("\n📊 RESULTADO:")
        print(f"   conversation_mode: {state.get('conversation_mode')}")
        print(f"   client_id: {state.get('client_id')}")
        print(f"   appointment_id: {state.get('appointment_id')}")
        print(f"   qualification_complete: {state.get('qualification_complete')}")
        print(f"   budget_qualified: {state.get('budget_qualified')}")
        print(f"   client_data: {state.get('client_data', {}).get('first_name')}")
        
        # 4. Assertions
        assertions = []
        
        if state.get("conversation_mode") == "returning_without_appointment":
            assertions.append("✅ conversation_mode correto (returning_without_appointment)")
        else:
            assertions.append(f"❌ conversation_mode esperado: returning_without_appointment, recebido: {state.get('conversation_mode')}")
        
        if state.get("client_id") == client_id:
            assertions.append("✅ client_id carregado corretamente")
        else:
            assertions.append("❌ client_id não corresponde")
        
        if state.get("appointment_id") is None:
            assertions.append("✅ appointment_id é None (sem appointment)")
        else:
            assertions.append(f"❌ appointment_id deveria ser None, recebido: {state.get('appointment_id')}")
        
        if state.get("qualification_complete") is False:
            assertions.append("✅ qualification_complete = False (precisa revalidar)")
        else:
            assertions.append("❌ qualification_complete deveria ser False")
        
        if state.get("budget_qualified") is True:
            assertions.append("✅ budget_qualified = True (baseado em dados antigos)")
        else:
            assertions.append("❌ budget_qualified deveria ser True")
        
        print("\n   " + "\n   ".join(assertions))
        
    finally:
        # 5. Cleanup
        print("\n🧹 CLEANUP: Removendo dados de teste...")
        await limpar_cliente_teste("71999888777")


async def test_cenario_3_cliente_novo():
    """
    CENÁRIO 3: Cliente NOVO (não existe no banco).
    
    Espera-se:
    - conversation_mode = None
    - Estado inicial vazio
    - qualification_complete = False
    - Fluxo normal de qualificação
    """
    print("\n" + "=" * 80)
    print("TESTE 3: Cliente NOVO (primeira interação)")
    print("=" * 80)
    
    print("\n🔍 TESTE: Carregando estado de cliente inexistente...")
    remote_jid = "5571999777666@s.whatsapp.net"  # Número que não existe
    phone = "71999777666"
    
    state = await carregar_state_do_usuario(remote_jid, phone)
    
    # Validar estado retornado
    print("\n📊 RESULTADO:")
    print(f"   conversation_mode: {state.get('conversation_mode')}")
    print(f"   client_id: {state.get('client_id')}")
    print(f"   qualification_complete: {state.get('qualification_complete')}")
    print(f"   phone: {state.get('phone')}")
    
    # Assertions
    assertions = []
    
    if state.get("conversation_mode") is None:
        assertions.append("✅ conversation_mode = None (cliente novo)")
    else:
        assertions.append(f"❌ conversation_mode deveria ser None, recebido: {state.get('conversation_mode')}")
    
    if state.get("client_id") is None:
        assertions.append("✅ client_id = None (ainda não criado)")
    else:
        assertions.append("❌ client_id deveria ser None")
    
    if state.get("qualification_complete") is False:
        assertions.append("✅ qualification_complete = False")
    else:
        assertions.append("❌ qualification_complete deveria ser False")
    
    if state.get("phone") == phone:
        assertions.append("✅ phone populado corretamente")
    else:
        assertions.append("❌ phone não corresponde")
    
    print("\n   " + "\n   ".join(assertions))


async def main():
    """Executa todos os testes."""
    print("\n🧪 TESTES DE MEMÓRIA PERSISTENTE DO AGENTE")
    print("=" * 80)
    
    try:
        await test_cenario_1_com_appointment()
        await test_cenario_2_sem_appointment()
        await test_cenario_3_cliente_novo()
        
        print("\n" + "=" * 80)
        print("✅ TODOS OS TESTES CONCLUÍDOS!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
