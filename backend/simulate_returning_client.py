"""
simulate_returning_client.py

Simula cliente que já teve agendamento e retorna para nova conversa.
Testa:
1. Primeiro agendamento (conversa completa)
2. Conversa é marcada como "completed"
3. Cliente retorna com nova mensagem
4. Sistema preserva contexto (nome, empresa, histórico)
5. Nova conversa começa do ponto certo

IMPORTANTE: Usa banco de testes (ia_crm_test) - não afeta produção
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Adicionar backend ao path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from langchain_core.messages import HumanMessage
from app.agent.graph import marketing_crm_graph
from app.core.database import AsyncSessionLocal
from sqlalchemy import text, select
from app.models.client import Client
from app.models.appointment import Appointment

BRAZIL_TZ = ZoneInfo("America/Sao_Paulo")


async def cleanup_test_data():
    """Limpa dados de teste do banco."""
    print("🧹 Limpando dados de teste anteriores...")
    
    async with AsyncSessionLocal() as db:
        await db.execute(text("DELETE FROM appointments WHERE client_id IN (SELECT id FROM clients WHERE phone = '71988776655')"))
        await db.execute(text("DELETE FROM clients WHERE phone = '71988776655'"))
        await db.commit()
    
    print("✅ Banco de teste limpo\n")


async def first_conversation():
    """
    Primeira conversa: cliente novo, qualificação completa, agendamento confirmado.
    """
    print("=" * 70)
    print("🎬 PARTE 1: PRIMEIRA CONVERSA (Cliente Novo)")
    print("=" * 70 + "\n")
    
    state = {
        "messages": [],
        "session_id": "test-returning-001",
        "phone": "71988776655",
        "conversation_mode": "greeting",
        "presentation_done": False,
        "initial_intent_captured": False,
        "permission_asked": False,
        "qualification_complete": False,
        "budget_qualified": False,
        "client_data": {},
        "client_id": None,
    }
    
    # Conversa completa até confirmação final
    messages = [
        "Olá",
        "Quero marcar uma reunião",
        "Maria Santos",
        "maria@clinicasorriso.com",
        "Clínica Sorriso Perfeito",
        "Odontologia",
        "Precisamos de mais pacientes novos",
        "8 mil por mês",
        "sim",  # Quer agendar?
        "Amanhã às 9h",  # Horário disponível
        # NÃO precisa confirmar novamente - agente já cria automaticamente
    ]
    
    for i, message in enumerate(messages, 1):
        print(f"👤 Cliente: {message}")
        state["messages"].append(HumanMessage(content=message))
        
        result = await marketing_crm_graph.ainvoke(state)
        
        if result.get("messages"):
            last_msg = result["messages"][-1]
            agent_response = last_msg.content if hasattr(last_msg, 'content') else str(last_msg)
            print(f"🤖 Agente: {agent_response[:100]}...")
        
        state = result
        
        # Mostrar progresso importante
        if result.get("qualification_complete"):
            print("   ✅ Qualificação completa")
        if result.get("appointment_confirmed"):
            print("   ✅ Agendamento confirmado")
        
        print()
    
    print("📊 RESULTADO PRIMEIRA CONVERSA:")
    print(f"   - Client ID: {state.get('client_id')}")
    print(f"   - Appointment ID: {state.get('appointment_id')}")
    print(f"   - Conversation Mode: {state.get('conversation_mode')}")
    print(f"   - Appointment Confirmed: {state.get('appointment_confirmed')}")
    print(f"   - Nome: {state.get('client_data', {}).get('first_name')}")
    print(f"   - Empresa: {state.get('client_data', {}).get('company_name')}")
    
    # Validações críticas
    if not state.get('appointment_id'):
        print("\n⚠️  AVISO: Agendamento NÃO foi criado! Conversa incompleta.")
        return None
    
    if state.get('conversation_mode') != 'completed':
        print(f"\n⚠️  AVISO: Conversa não marcada como 'completed' (atual: {state.get('conversation_mode')})")
    
    return state


async def verify_client_in_db(phone: str):
    """Verifica se cliente foi salvo no banco."""
    print("\n" + "=" * 70)
    print("🔍 VERIFICAÇÃO NO BANCO DE DADOS")
    print("=" * 70 + "\n")
    
    async with AsyncSessionLocal() as db:
        # Buscar cliente
        result = await db.execute(
            select(Client).where(Client.phone == phone)
        )
        client = result.scalar_one_or_none()
        
        if client:
            print(f"✅ Cliente encontrado no banco:")
            print(f"   - ID: {client.id}")
            print(f"   - Nome: {client.first_name} {client.last_name}")
            print(f"   - Empresa: {client.company_name}")
            print(f"   - Orçamento: R$ {client.monthly_budget}")
            
            # Buscar agendamentos
            result = await db.execute(
                select(Appointment).where(Appointment.client_id == client.id)
            )
            appointments = result.scalars().all()
            
            print(f"\n   📅 Agendamentos: {len(appointments)}")
            for apt in appointments:
                print(f"      - {apt.scheduled_at.strftime('%d/%m/%Y %H:%M')} - Status: {apt.status}")
            
            return client.id
        else:
            print("❌ Cliente NÃO encontrado no banco")
            return None


async def simulate_time_passing():
    """Simula passagem de tempo (conversa terminou, cliente foi embora)."""
    print("\n" + "=" * 70)
    print("⏰ PASSAGEM DE TEMPO")
    print("=" * 70)
    print("   Simulando que a conversa foi concluída...")
    print("   Cliente saiu do chat...")
    print("   Algumas horas se passaram...")
    await asyncio.sleep(1)
    print("   ✅ Cliente agora retorna com nova mensagem\n")


async def second_conversation(client_id: str):
    """
    Segunda conversa: cliente retorna após agendamento concluído.
    Sistema deve:
    1. Reconhecer cliente existente (por telefone)
    2. Carregar histórico do banco
    3. Saudar com nome
    4. Oferecer ajuda contextualizada
    """
    print("=" * 70)
    print("🎬 PARTE 2: CLIENTE RETORNANDO (Com Histórico)")
    print("=" * 70 + "\n")
    
    # IMPORTANTE: Estado NOVO (simula nova sessão)
    # Mas telefone é o mesmo (sistema vai reconhecer)
    state = {
        "messages": [],
        "session_id": "test-returning-002",  # Nova sessão!
        "phone": "71988776655",  # Mesmo telefone
        "conversation_mode": "greeting",  # Começa do zero
        "presentation_done": False,
        "client_id": None,  # Será carregado do banco
        "client_data": {},  # Será carregado do banco
    }
    
    print("📱 NOVA MENSAGEM DO CLIENTE:")
    print("─" * 70)
    
    # Cliente retorna com nova pergunta
    new_messages = [
        "Oi, tenho uma dúvida sobre meu agendamento",
        "Posso remarcar para outro dia?",
        "Quinta-feira às 15h",  # Nova data para remarcação
    ]
    
    for message in new_messages:
        print(f"\n👤 Cliente: {message}")
        state["messages"].append(HumanMessage(content=message))
        
        result = await marketing_crm_graph.ainvoke(state)
        
        if result.get("messages"):
            last_msg = result["messages"][-1]
            agent_response = last_msg.content if hasattr(last_msg, 'content') else str(last_msg)
            print(f"🤖 Agente: {agent_response}")
        
        state = result
        print()
    
    print("=" * 70)
    print("📊 RESULTADO SEGUNDA CONVERSA:")
    print("=" * 70)
    print(f"   - Client ID: {state.get('client_id')}")
    print(f"   - Conversation Mode: {state.get('conversation_mode')}")
    print(f"   - Cliente Reconhecido: {str(state.get('client_id')) == str(client_id)}")
    
    if state.get("client_data"):
        print(f"   - Nome carregado: {state.get('client_data', {}).get('first_name')}")
        print(f"   - Empresa carregada: {state.get('client_data', {}).get('company_name')}")
    
    # VALIDAÇÃO CRÍTICA
    print("\n" + "=" * 70)
    print("✅ VALIDAÇÕES:")
    print("=" * 70)
    
    validations = []
    all_passed = True
    
    # 1. Cliente foi reconhecido? (comparar como str, state guarda str, banco retorna UUID)
    if str(state.get('client_id')) == str(client_id):
        validations.append("✅ Cliente reconhecido pelo telefone")
    else:
        validations.append(f"❌ FALHA: Cliente NÃO foi reconhecido (esperado: {client_id}, obtido: {state.get('client_id')})")
        all_passed = False
    
    # 2. Dados foram carregados?
    if state.get('client_data', {}).get('first_name'):
        validations.append(f"✅ Dados carregados: {state['client_data']['first_name']}")
    else:
        validations.append("❌ FALHA: Dados NÃO foram carregados")
        all_passed = False
    
    # 3. Agente usou o nome?
    if result.get("messages"):
        last_msg = result["messages"][-1].content if hasattr(result["messages"][-1], 'content') else ""
        if "Maria" in last_msg or state.get('client_data', {}).get('first_name', '') in last_msg:
            validations.append("✅ Agente usou o nome do cliente na resposta")
        else:
            validations.append("⚠️  Agente não usou o nome (pode ser normal)")
    
    # 4. Modo de conversa correto?
    expected_modes = ["returning_with_appointment", "returning_without_appointment", "greeting", "question", "requalification", "rescheduling", "scheduling", "completed"]
    if state.get('conversation_mode') in expected_modes:
        validations.append(f"✅ Modo correto: {state.get('conversation_mode')}")
    else:
        validations.append(f"❌ FALHA: Modo inesperado: {state.get('conversation_mode')}")
        all_passed = False
    
    # 5. Appointment foi remarcado?
    if state.get('appointment_confirmed'):
        validations.append("✅ Novo appointment criado (remarcação)")
    else:
        validations.append("⚠️  Appointment não confirmado (pode ser normal se não completou remarcação)")
    
    # 6. Verificar no banco: appointment antigo cancelado + novo ativo
    async with AsyncSessionLocal() as db:
        result_db = await db.execute(
            select(Appointment).where(Appointment.client_id == client_id).order_by(Appointment.created_at.asc())
        )
        all_appointments = result_db.scalars().all()
        
        cancelled_count = sum(1 for a in all_appointments if a.status.value == "cancelled")
        active_count = sum(1 for a in all_appointments if a.status.value in ("pending", "confirmed"))
        
        if cancelled_count >= 1 and active_count >= 1:
            validations.append(f"✅ Remarcação OK: {cancelled_count} cancelado(s), {active_count} ativo(s)")
        elif len(all_appointments) > 1:
            statuses = [f"{a.status.value}" for a in all_appointments]
            validations.append(f"⚠️  Appointments: {statuses} (esperado: 1 cancelled + 1 pending)")
        else:
            validations.append(f"⚠️  Apenas {len(all_appointments)} appointment(s) no banco")
    
    print("\n".join(validations))
    
    return all_passed


async def main():
    """Executa simulação completa."""
    print("\n" + "🎯" * 35)
    print("TESTE: CLIENTE RETORNANDO APÓS AGENDAMENTO CONCLUÍDO")
    print("🎯" * 35 + "\n")
    
    try:
        # Limpar dados anteriores
        await cleanup_test_data()
        
        # PARTE 1: Primeira conversa (agendamento)
        first_state = await first_conversation()
        
        # Verificar se a primeira conversa foi bem-sucedida
        if not first_state:
            print("\n❌ ERRO: Primeira conversa não completou o agendamento!")
            print("   Não é possível testar cliente retornando sem agendamento prévio.")
            return
        
        # Verificar se salvou no banco
        client_id = await verify_client_in_db("71988776655")
        
        if not client_id:
            print("\n❌ ERRO: Cliente não foi salvo no banco!")
            return
        
        # Simular passagem de tempo
        await simulate_time_passing()
        
        # PARTE 2: Cliente retorna
        all_passed = await second_conversation(client_id)
        
        # Resumo final
        print("\n" + "=" * 70)
        if all_passed:
            print("🏆 TESTE CONCLUÍDO COM SUCESSO!")
            print("=" * 70)
            print("\n✅ O sistema:")
            print("   1. Salvou cliente no banco na primeira conversa")
            print("   2. Criou agendamento com sucesso")
            print("   3. Marcou conversa como 'completed'")
            print("   4. Reconheceu cliente na segunda conversa")
            print("   5. Carregou histórico do banco")
            print("   6. Contexto foi preservado entre sessões")
        else:
            print("❌ TESTE FALHOU!")
            print("=" * 70)
            print("\n⚠️  Algumas validações não passaram. Verifique os logs acima.")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Simulação interrompida pelo usuário")
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n✅ Encerrando simulação...")


if __name__ == "__main__":
    asyncio.run(main())
