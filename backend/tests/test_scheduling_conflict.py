"""
Script de teste para validar comportamento do agente em cenário de conflito de horário.

CENÁRIO:
1. Cria appointment no banco para amanhã às 14h
2. Injeta estado simulado de cliente já qualificado
3. Cliente solicita exatamente esse horário ocupado
4. Valida se agente oferece alternativas corretamente

OBJETIVO: Testar fluxo de alternative_slots sem passar pela qualificação.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from uuid import uuid4
from decimal import Decimal

# Adicionar backend ao path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from langchain_core.messages import HumanMessage
from app.agent.graph import marketing_crm_graph
from app.core.database import AsyncSessionLocal
from app.models.client import Client
from app.models.appointment import Appointment, AppointmentStatus
from app.schemas.clientSchema import ClientSegment
from zoneinfo import ZoneInfo

BRAZIL_TZ = ZoneInfo("America/Sao_Paulo")


async def setup_test_scenario():
    """
    Cria cenário de teste:
    1. Cliente de teste no banco
    2. Appointment ocupando amanhã às 14h
    
    Retorna: (client_id, occupied_datetime)
    """
    print("🛠️  SETUP: Criando cenário de teste...")
    
    async with AsyncSessionLocal() as db:
        # 1. Criar cliente de teste
        test_client = Client(
            id=uuid4(),
            first_name="João",
            last_name="Teste",
            phone="71999999999",  # Número fake para teste
            email="joao.teste@example.com",
            company_name="Empresa Teste Ltda",
            segment=ClientSegment.CLINICA_ODONTOLOGICA,
            monthly_budget=Decimal("8000.00"),
            main_marketing_problem="Teste de conflito de horário"
        )
        db.add(test_client)
        await db.flush()
        
        # 2. Criar appointment ocupando amanhã às 14h
        tomorrow_14h = datetime.now(BRAZIL_TZ).replace(
            hour=14, minute=0, second=0, microsecond=0
        ) + timedelta(days=1)
        
        occupied_appointment = Appointment(
            id=uuid4(),
            client_id=test_client.id,
            scheduled_at=tomorrow_14h,
            duration_minutes=30,
            meeting_type="CONSULTORIA_INICIAL",
            status=AppointmentStatus.PENDING
        )
        db.add(occupied_appointment)
        await db.commit()
        
        print(f"✅ Cliente criado: {test_client.first_name} {test_client.last_name}")
        print(f"✅ Appointment ocupado criado: {tomorrow_14h.strftime('%d/%m/%Y às %H:%M')}")
        print(f"   Client ID: {test_client.id}")
        print(f"   Appointment ID: {occupied_appointment.id}")
        
        return str(test_client.id), tomorrow_14h


async def cleanup_test_data(client_id: str):
    """Remove dados de teste do banco."""
    print("\n🧹 CLEANUP: Removendo dados de teste...")
    
    async with AsyncSessionLocal() as db:
        # Deleta appointments do cliente de teste
        from sqlalchemy import delete
        await db.execute(
            delete(Appointment).where(Appointment.client_id == client_id)
        )
        
        # Deleta cliente de teste
        await db.execute(
            delete(Client).where(Client.id == client_id)
        )
        
        await db.commit()
        print("✅ Dados de teste removidos")


async def test_scheduling_conflict():
    """
    Testa comportamento do agente quando cliente solicita horário ocupado.
    """
    print("=" * 70)
    print("TESTE DE CONFLITO DE AGENDAMENTO")
    print("=" * 70)
    
    # 1. SETUP: Criar cenário
    client_id, occupied_datetime = await setup_test_scenario()
    
    try:
        # 2. Criar estado simulado (cliente já qualificado)
        print("\n📊 Criando estado simulado (pula qualificação)...")
        
        simulated_state = {
            "messages": [
                HumanMessage(content="Olá, quero agendar uma reunião")
            ],
            "session_id": "test-conflict-001",
            "phone": "71988888888",  # Número do solicitante (diferente do ocupante)
            
            # SIMULAR QUALIFICAÇÃO COMPLETA
            "presentation_done": True,
            "initial_intent_captured": True,
            "initial_intent": "wants_meeting",
            "permission_asked": True,
            "qualification_complete": True,
            "budget_qualified": True,
            
            # DADOS DO CLIENTE (simulado)
            "client_data": {
                "first_name": "Maria",
                "last_name": "Silva",
                "email": "maria.silva@example.com",
                "company_name": "Silva Odonto",
                "segment": "CLINICA_ODONTOLOGICA",
                "monthly_budget": "10000.00",
                "main_marketing_problem": "Baixa conversão de leads"
            },
            "client_id": None,  # Será criado pelo agente
            
            # MODO DE CONVERSA: PULAR DIRETO PARA AGENDAMENTO
            "conversation_mode": "scheduling",
            
            # FLAGS DE AGENDAMENTO
            "asked_to_schedule": False,
            "wants_to_schedule": None,
            "requested_datetime": None,
            "slot_available": None,
            "alternative_slots": None,
            "chosen_slot": None,
            "appointment_confirmed": False
        }
        
        print("✅ Estado simulado criado")
        print(f"   conversation_mode: scheduling")
        print(f"   qualification_complete: True")
        print(f"   budget_qualified: True")
        print(f"   Cliente simulado: Maria Silva (Silva Odonto)")
        
        # 3. EXECUÇÃO 1: Agente oferece agendamento
        print("\n" + "─" * 70)
        print("🤖 EXECUÇÃO 1: Agente oferece reunião")
        print("─" * 70)
        
        result = await marketing_crm_graph.ainvoke(simulated_state)
        
        last_message = result["messages"][-1].content
        print(f"\n🤖 AGENTE: {last_message}\n")
        
        # 4. EXECUÇÃO 2: Cliente solicita horário OCUPADO
        print("─" * 70)
        print("👤 CLIENTE: Solicita horário ocupado")
        print("─" * 70)
        
        # Formatar data no formato brasileiro
        requested_time = occupied_datetime.strftime("%d/%m/%Y às %H:%M")
        user_request = f"Quero agendar para {requested_time}"
        
        print(f"👤 VOCÊ: {user_request}")
        result["messages"].append(HumanMessage(content=user_request))
        
        result = await marketing_crm_graph.ainvoke(result)
        
        last_message = result["messages"][-1].content
        print(f"\n🤖 AGENTE: {last_message}\n")
        
        # 5. VALIDAÇÃO: Verificar se ofereceu alternativas
        print("=" * 70)
        print("VALIDAÇÃO DOS RESULTADOS")
        print("=" * 70)
        
        print(f"✓ requested_datetime: {result.get('requested_datetime')}")
        print(f"✓ slot_available: {result.get('slot_available')}")
        print(f"✓ alternative_slots: {result.get('alternative_slots')}")
        print(f"✓ conversation_mode: {result.get('conversation_mode')}")
        
        # Verificações
        assertions = []
        
        if result.get("slot_available") is False:
            assertions.append("✅ Detectou horário indisponível")
        else:
            assertions.append("❌ FALHA: Não detectou conflito")
        
        if result.get("alternative_slots"):
            assertions.append("✅ Ofereceu horários alternativos")
        else:
            assertions.append("❌ FALHA: Não ofereceu alternativas")
        
        if "alternativa" in last_message.lower() or "disponível" in last_message.lower():
            assertions.append("✅ Mensagem comunica indisponibilidade")
        else:
            assertions.append("⚠️  Mensagem pode ser mais clara sobre indisponibilidade")
        
        print("\n" + "\n".join(assertions))
        
        # 6. TESTE ADICIONAL: Escolher horário alternativo
        if result.get("alternative_slots"):
            print("\n" + "─" * 70)
            print("👤 CLIENTE: Escolhe horário alternativo")
            print("─" * 70)
            
            # Simular escolha do próximo slot
            user_choice = "Pode ser o próximo horário disponível"
            print(f"👤 VOCÊ: {user_choice}")
            result["messages"].append(HumanMessage(content=user_choice))
            
            result = await marketing_crm_graph.ainvoke(result)
            
            last_message = result["messages"][-1].content
            print(f"\n🤖 AGENTE: {last_message}\n")
            
            if result.get("appointment_confirmed"):
                print("✅ Appointment criado com horário alternativo!")
            else:
                print("⚠️  Appointment ainda não confirmado")
        
        print("\n" + "=" * 70)
        print("🎉 TESTE CONCLUÍDO!")
        print("=" * 70)
        
    finally:
        # 7. CLEANUP: Remover dados de teste
        await cleanup_test_data(client_id)


async def main():
    """Executa o teste."""
    try:
        await test_scheduling_conflict()
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
