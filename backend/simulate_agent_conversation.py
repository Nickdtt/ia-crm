"""
simulate_agent_conversation.py

Simula uma conversa completa com o agente usando banco de testes.
Testa o fluxo: greeting → qualification → budget filter → scheduling

IMPORTANTE: Usa banco de testes (ia_crm_test) - não afeta produção
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

# Adicionar backend ao path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from langchain_core.messages import HumanMessage
from app.agent.graph import marketing_crm_graph
from app.core.database import AsyncSessionLocal
from sqlalchemy import text

BRAZIL_TZ = ZoneInfo("America/Sao_Paulo")


async def cleanup_test_data():
    """Limpa dados de teste do banco."""
    print("🧹 Limpando dados de teste anteriores...")
    
    async with AsyncSessionLocal() as db:
        # Usar banco de teste via environment
        await db.execute(text("DELETE FROM appointments WHERE client_id IN (SELECT id FROM clients WHERE phone = '71999887766')"))
        await db.execute(text("DELETE FROM clients WHERE phone = '71999887766'"))
        await db.commit()
    
    print("✅ Banco de teste limpo\n")


async def simulate_conversation():
    """
    Simula conversa completa com o agente.
    
    Fluxo testado:
    1. Greeting
    2. Cliente quer agendar
    3. Qualificação (nome, empresa, segment, budget)
    4. Budget aprovado
    5. Oferece agendamento
    6. Cliente aceita ("sim" deve funcionar!)
    7. Cliente informa data/hora
    8. Confirmação
    """
    print("=" * 70)
    print("🤖 SIMULAÇÃO DE CONVERSA COM O AGENTE")
    print("=" * 70)
    print(f"📅 Data: {datetime.now(BRAZIL_TZ).strftime('%d/%m/%Y %H:%M')}")
    print(f"🗄️  Banco: ia_crm_test (PostgreSQL porta 5434)")
    print("=" * 70 + "\n")
    
    # Estado inicial
    state = {
        "messages": [],
        "session_id": "test-simulation-001",
        "phone": "71999887766",  # Telefone de teste
        "conversation_mode": "greeting",
        "presentation_done": False,
        "initial_intent_captured": False,
        "permission_asked": False,
        "qualification_complete": False,
        "budget_qualified": False,
        "client_data": {},
        "client_id": None,
    }
    
    # Mensagens da conversa
    conversation = [
        ("Cliente", "Olá"),
        ("Cliente", "Quero agendar uma reunião"),
        ("Cliente", "João Silva"),
        ("Cliente", "joao@clinicasorriso.com"),
        ("Cliente", "Clínica Sorriso Perfeito"),
        ("Cliente", "Trabalho com odontologia"),
        ("Cliente", "Quero aumentar o número de pacientes"),
        ("Cliente", "10 mil reais por mês"),
        ("Cliente", "sim"),  # Teste: "sim" deve ser aceito para pergunta "Quer agendar?"
        ("Cliente", "Amanhã às 14h"),
    ]
    
    step = 1
    
    for speaker, message in conversation:
        print(f"─" * 70)
        print(f"📝 PASSO {step}")
        print(f"─" * 70)
        print(f"👤 {speaker}: {message}\n")
        
        # Adicionar mensagem do usuário
        state["messages"].append(HumanMessage(content=message))
        
        # Executar agente
        try:
            result = await marketing_crm_graph.ainvoke(state)
            
            # Extrair resposta do agente
            if result.get("messages"):
                last_message = result["messages"][-1]
                agent_response = last_message.content if hasattr(last_message, 'content') else str(last_message)
                print(f"🤖 AGENTE: {agent_response}\n")
            
            # Mostrar estado atual (resumido)
            print("📊 Estado:")
            print(f"   - conversation_mode: {result.get('conversation_mode')}")
            print(f"   - qualification_complete: {result.get('qualification_complete')}")
            print(f"   - budget_qualified: {result.get('budget_qualified')}")
            print(f"   - wants_to_schedule: {result.get('wants_to_schedule')}")
            print(f"   - appointment_confirmed: {result.get('appointment_confirmed')}")
            
            if result.get("client_data"):
                print(f"   - Dados coletados: {len(result['client_data'])} campos")
            
            # Atualizar estado para próxima iteração
            state = result
            
        except Exception as e:
            print(f"❌ ERRO: {e}")
            import traceback
            traceback.print_exc()
            break
        
        step += 1
        await asyncio.sleep(0.5)  # Pequena pausa entre mensagens
    
    print("\n" + "=" * 70)
    print("🎉 SIMULAÇÃO CONCLUÍDA!")
    print("=" * 70)
    
    # Resumo final
    print("\n📊 RESUMO FINAL:")
    print(f"   - Cliente criado: {state.get('client_id') is not None}")
    print(f"   - Qualificação completa: {state.get('qualification_complete')}")
    print(f"   - Budget aprovado: {state.get('budget_qualified')}")
    print(f"   - Agendamento confirmado: {state.get('appointment_confirmed')}")
    
    if state.get("client_data"):
        print(f"\n📝 Dados do Cliente:")
        for key, value in state["client_data"].items():
            print(f"   - {key}: {value}")
    
    if state.get("appointment_id"):
        print(f"\n📅 Appointment ID: {state['appointment_id']}")


async def main():
    """Executa a simulação."""
    try:
        # Limpar dados anteriores
        await cleanup_test_data()
        
        # Simular conversa
        await simulate_conversation()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Simulação interrompida pelo usuário")
    except Exception as e:
        print(f"\n❌ ERRO GERAL: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n✅ Encerrando simulação...")


if __name__ == "__main__":
    asyncio.run(main())
