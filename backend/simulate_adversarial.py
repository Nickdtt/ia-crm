"""
simulate_adversarial.py

Cenários ADVERSARIAIS para testar o Intent Guard.
O cliente envia intenções erradas NO MEIO de fluxos ativos.

Sem o Guard, o agente processa normalmente e fica confuso.
Com o Guard, o agente detecta, responde adequadamente e mantém o fluxo.

CENÁRIOS:
  A1. Cliente em qualificação manda "quero cancelar minha reunião" (sem ter reunião)
  A2. Cliente em qualificação pede para encerrar ("não tenho mais interesse")
  A3. Cliente em qualificação pergunta sobre preço no meio dos dados
  A4. Cliente em qualificação manda spam/emoji/nonsense
  A5. Cliente em agendamento quer mudar a data no meio
  A6. Paciente (fora de escopo) durante qualificação
  A7. Cliente em agendamento quer encerrar sem agendar
  A8. Sequência: qualificação → pergunta → retoma qualificação
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from decimal import Decimal

from dotenv import load_dotenv
_env_path = Path(__file__).parent.parent / ".env"
load_dotenv(str(_env_path))

backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from langchain_core.messages import HumanMessage, AIMessage

# Sempre com Guard
from app.agent.graph_with_guard import marketing_crm_graph_guarded as marketing_crm_graph

from app.core.database import AsyncSessionLocal
from app.models.client import Client
from app.models.appointment import Appointment, AppointmentStatus
from app.schemas.clientSchema import ClientCreate, ClientSegment
from app.services.clientService import create_client
from sqlalchemy import text

BRAZIL_TZ = ZoneInfo("America/Sao_Paulo")

# Telefones adversariais (range 71900001001–71900001008)
PHONES = {
    "A1": "71900001001",
    "A2": "71900001002",
    "A3": "71900001003",
    "A4": "71900001004",
    "A5": "71900001005",
    "A6": "71900001006",
    "A7": "71900001007",
    "A8": "71900001008",
}

results = []


def new_state(phone: str) -> dict:
    return {
        "messages": [],
        "session_id": f"adv-{phone}",
        "phone": phone,
        "conversation_mode": "greeting",
        "presentation_done": False,
        "initial_intent_captured": False,
        "permission_asked": False,
        "qualification_complete": False,
        "budget_qualified": False,
        "client_data": {},
        "client_id": None,
    }


async def send_message(state: dict, message: str) -> dict:
    state["messages"].append(HumanMessage(content=message))
    try:
        result = await marketing_crm_graph.ainvoke(state)
        agent_response = ""
        if result.get("messages"):
            last_msg = result["messages"][-1]
            if isinstance(last_msg, AIMessage):
                agent_response = last_msg.content
        print(f"  👤 Cliente: {message}")
        if agent_response:
            display = agent_response[:160] + "..." if len(agent_response) > 160 else agent_response
            print(f"  🤖 Agente:  {display}")
        print(f"     mode={result.get('conversation_mode')} | guard={result.get('interrupt_intent')} | step={result.get('current_step')}")
        print()
        return result
    except Exception as e:
        print(f"  ❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return state


async def cleanup():
    async with AsyncSessionLocal() as db:
        for phone in PHONES.values():
            await db.execute(text(
                f"DELETE FROM appointments WHERE client_id IN (SELECT id FROM clients WHERE phone = '{phone}')"
            ))
            await db.execute(text(f"DELETE FROM clients WHERE phone = '{phone}'"))
        await db.commit()
    print("✅ Banco adversarial limpo\n")


def record(key: str, name: str, passed: bool, what_happened: str, expected: str):
    status = "✅ PASSOU" if passed else "❌ FALHOU"
    results.append((key, name, passed, what_happened, expected))
    print(f"\n  {'='*65}")
    print(f"  {status}: Cenário {key} — {name}")
    print(f"  🎯 Esperado:    {expected}")
    print(f"  📋 O que houve: {what_happened}")
    print(f"  {'='*65}\n")


# ═══════════════════════════════════════════════════════════════════
# A1: "Quero cancelar minha reunião" durante qualificação (sem reunião)
# ═══════════════════════════════════════════════════════════════════
async def scenario_A1():
    print("\n" + "🔴" * 30)
    print("CENÁRIO A1: 'QUERO CANCELAR' DURANTE QUALIFICAÇÃO (sem ter reunião)")
    print("🔴" * 30 + "\n")

    phone = PHONES["A1"]
    state = new_state(phone)

    # Começa qualificação normalmente
    state = await send_message(state, "Oi, quero marcar uma reunião")
    state = await send_message(state, "João Silva")
    state = await send_message(state, "joao@clinica.com")
    # No meio, manda intenção errada
    state = await send_message(state, "Na verdade, quero cancelar minha reunião")

    # O Guard deve: detectar que não faz sentido cancelar sem ter reunião,
    # tratar como wants_exit ou off_topic, NÃO como cancelamento real.
    # O agente NÃO deve tentar buscar appointment (que não existe).
    guard = state.get("interrupt_intent")
    mode = state.get("conversation_mode")
    agent_msg = ""
    if state.get("messages"):
        last = state["messages"][-1]
        if isinstance(last, AIMessage):
            agent_msg = last.content.lower()

    # Não deve ter crashado tentando cancelar appointment inexistente
    no_crash = bool(agent_msg)
    # Guard atuou (saiu do "continue") OU agente tratou sem crash
    guard_acted = guard in ("wants_exit", "off_topic", "wants_question") or "cancelar" in agent_msg
    # NÃO deve estar em modo cancelled/completed por cancelamento de appointment
    not_broken = mode != "cancelled"

    passed = no_crash and not_broken
    what = f"guard={guard} | mode={mode} | resposta: '{agent_msg[:80]}'"
    expected = "Guard detecta intent incoerente, não crashar tentando cancelar appointment inexistente"
    record("A1", "'Cancelar reunião' durante qualificação", passed, what, expected)


# ═══════════════════════════════════════════════════════════════════
# A2: Cliente diz "não tenho mais interesse" no meio da qualificação
# ═══════════════════════════════════════════════════════════════════
async def scenario_A2():
    print("\n" + "🚪" * 30)
    print("CENÁRIO A2: 'NÃO TENHO MAIS INTERESSE' DURANTE QUALIFICAÇÃO")
    print("🚪" * 30 + "\n")

    phone = PHONES["A2"]
    state = new_state(phone)

    state = await send_message(state, "Oi, quero uma reunião")
    state = await send_message(state, "Maria Fernanda")
    state = await send_message(state, "maria@clinica.com")
    state = await send_message(state, "Clínica Fernanda")
    # Interrompe no meio com saída
    state = await send_message(state, "não tenho mais interesse, obrigada")

    guard = state.get("interrupt_intent")
    mode = state.get("conversation_mode")
    agent_msg = ""
    if state.get("messages"):
        last = state["messages"][-1]
        if isinstance(last, AIMessage):
            agent_msg = last.content.lower()

    # Guard deve detectar wants_exit e encerrar educadamente
    guard_exit = guard == "wants_exit"
    mode_completed = mode == "completed"
    polite_farewell = any(w in agent_msg for w in ["tudo bem", "sem pressão", "tchau", "qualquer momento", "até mais", "fique à vontade"])

    passed = guard_exit and mode_completed and polite_farewell
    what = f"guard={guard} | mode={mode} | despedida educada={polite_farewell}"
    expected = "guard=wants_exit | mode=completed | resposta de despedida educada"
    record("A2", "'Não tenho mais interesse' durante qualificação", passed, what, expected)


# ═══════════════════════════════════════════════════════════════════
# A3: Pergunta sobre preço no meio da coleta de dados
# ═══════════════════════════════════════════════════════════════════
async def scenario_A3():
    print("\n" + "❓" * 30)
    print("CENÁRIO A3: PERGUNTA SOBRE PREÇO NO MEIO DA QUALIFICAÇÃO")
    print("❓" * 30 + "\n")

    phone = PHONES["A3"]
    state = new_state(phone)

    state = await send_message(state, "Oi")
    state = await send_message(state, "Quero agendar")
    state = await send_message(state, "Roberto Alves")
    state = await send_message(state, "roberto@clinica.com")
    # Pergunta fora de contexto
    state = await send_message(state, "Quanto vocês cobram? Qual é o preço do serviço de vocês?")

    guard = state.get("interrupt_intent")
    mode_after = state.get("conversation_mode")
    agent_msg = ""
    if state.get("messages"):
        last = state["messages"][-1]
        if isinstance(last, AIMessage):
            agent_msg = last.content.lower()

    # Guard deve detectar wants_question
    guard_question = guard == "wants_question"
    # Agente deve ter respondido sobre preço/proposta
    answered = any(w in agent_msg for w in ["proposta", "valor", "preço", "investimento", "reunião", "conversar", "personaliz"])

    passed = guard_question and answered
    what = f"guard={guard} | mode={mode_after} | respondeu sobre preço={answered}"
    expected = "guard=wants_question | agente responde a pergunta antes de retomar qualificação"
    record("A3", "Pergunta sobre preço no meio da qualificação", passed, what, expected)


# ═══════════════════════════════════════════════════════════════════
# A4: Spam / emoji / nonsense durante qualificação ativa
# ═══════════════════════════════════════════════════════════════════
async def scenario_A4():
    print("\n" + "🤡" * 30)
    print("CENÁRIO A4: SPAM / EMOJI / NONSENSE DURANTE QUALIFICAÇÃO ATIVA")
    print("🤡" * 30 + "\n")

    phone = PHONES["A4"]
    state = new_state(phone)

    # Já está em qualificação
    state = await send_message(state, "Oi, quero agendar")
    state = await send_message(state, "Luciana Rocha")
    state = await send_message(state, "luciana@clinica.com")
    # Spam
    state = await send_message(state, "kkkkkkkk 🤣🤣🤣🤣")
    state = await send_message(state, "oi oi oi oi")
    state = await send_message(state, "😂😂😂")
    # Retoma normalmente após o Guard tratar os off_topics
    state = await send_message(state, "Clínica Luciana")

    guard = state.get("interrupt_intent")
    mode = state.get("conversation_mode")
    client_data = state.get("client_data", {})

    # O agente deve ter mantido os dados já coletados (nome, email)
    kept_name = bool(client_data.get("first_name") or client_data.get("full_name"))
    not_crashed = mode in ("qualification", "greeting", "scheduling", "completed")

    passed = kept_name and not_crashed
    what = f"guard={guard} | mode={mode} | dados mantidos: nome={client_data.get('first_name')} | mode={mode}"
    expected = "Guard trata off_topic com nudge, mantém dados já coletados, não perde o contexto"
    record("A4", "Spam/emoji durante qualificação ativa", passed, what, expected)


# ═══════════════════════════════════════════════════════════════════
# A5: Muda a data no meio do processo de agendamento
# ═══════════════════════════════════════════════════════════════════
async def scenario_A5():
    print("\n" + "📅" * 30)
    print("CENÁRIO A5: MUDA A DATA DURANTE AGENDAMENTO")
    print("📅" * 30 + "\n")

    phone = PHONES["A5"]
    state = new_state(phone)

    # Qualificação completa até offer scheduling
    state = await send_message(state, "Oi")
    state = await send_message(state, "Quero agendar")
    state = await send_message(state, "Bruno Carvalho")
    state = await send_message(state, "bruno@clinicabruno.com")
    state = await send_message(state, "Clínica Bruno")
    state = await send_message(state, "Clínica médica")
    state = await send_message(state, "Preciso de mais pacientes")
    state = await send_message(state, "8 mil")
    state = await send_message(state, "sim")
    # Entra em scheduling e propõe uma data
    state = await send_message(state, "Quarta-feira às 14h")

    # No meio, pede para mudar
    state = await send_message(state, "espera, pode ser sexta às 9h em vez disso?")

    guard = state.get("interrupt_intent")
    mode = state.get("conversation_mode")
    requested_dt = state.get("requested_datetime")
    agent_msg = ""
    if state.get("messages"):
        last = state["messages"][-1]
        if isinstance(last, AIMessage):
            agent_msg = last.content.lower()

    # Guard deve detectar wants_reschedule e resetar datetime
    guard_reschedule = guard == "wants_reschedule"
    dt_reset = requested_dt is None
    # Agente deve ter perguntado nova data
    asked_new_date = any(w in agent_msg for w in ["qual", "data", "horário", "quando", "prefere", "sexta", "9h", "09:00"])

    passed = guard_reschedule and dt_reset and asked_new_date
    what = f"guard={guard} | dt_reset={dt_reset} | asked_new_date={asked_new_date}"
    expected = "guard=wants_reschedule | requested_datetime=None | agente pergunta nova data"
    record("A5", "Muda data durante agendamento", passed, what, expected)


# ═══════════════════════════════════════════════════════════════════
# A6: Paciente buscando atendimento (fora de escopo) durante qualificação
# ═══════════════════════════════════════════════════════════════════
async def scenario_A6():
    print("\n" + "🏥" * 30)
    print("CENÁRIO A6: PACIENTE BUSCANDO ATENDIMENTO (FORA DE ESCOPO)")
    print("🏥" * 30 + "\n")

    phone = PHONES["A6"]
    state = new_state(phone)

    # Começa como se fosse cliente B2B
    state = await send_message(state, "Oi")
    state = await send_message(state, "Gostaria de agendar")
    state = await send_message(state, "Ana Lima")
    # Revela ser paciente
    state = await send_message(state, "quero marcar uma consulta, sou paciente de ortopedia")

    guard = state.get("interrupt_intent")
    mode = state.get("conversation_mode")
    agent_msg = ""
    if state.get("messages"):
        last = state["messages"][-1]
        if isinstance(last, AIMessage):
            agent_msg = last.content.lower()

    # Guard deve detectar out_of_scope
    guard_scope = guard == "out_of_scope"
    mode_completed = mode == "completed"
    clarified = any(w in agent_msg for w in ["paciente", "agência", "clínica", "dono", "negócio", "marketing", "captação"])

    passed = guard_scope and mode_completed and clarified
    what = f"guard={guard} | mode={mode} | esclareceu contexto={clarified}"
    expected = "guard=out_of_scope | mode=completed | explica que atende donos de clínica, não pacientes"
    record("A6", "Paciente fora de escopo durante qualificação", passed, what, expected)


# ═══════════════════════════════════════════════════════════════════
# A7: Cliente em fase de agendamento decide encerrar
# ═══════════════════════════════════════════════════════════════════
async def scenario_A7():
    print("\n" + "🚫" * 30)
    print("CENÁRIO A7: 'ESQUECE' DURANTE AGENDAMENTO")
    print("🚫" * 30 + "\n")

    phone = PHONES["A7"]
    state = new_state(phone)

    # Qualificação completa
    state = await send_message(state, "Oi")
    state = await send_message(state, "Quero uma reunião")
    state = await send_message(state, "Tatiana Bispo")
    state = await send_message(state, "tatiana@clinica.com")
    state = await send_message(state, "Clínica Tatiana")
    state = await send_message(state, "Nutricionista")
    state = await send_message(state, "Quero mais clientes")
    state = await send_message(state, "5 mil")
    state = await send_message(state, "sim")
    # No momento de escolher horário, desiste
    state = await send_message(state, "esquece, não quero mais")

    guard = state.get("interrupt_intent")
    mode = state.get("conversation_mode")
    agent_msg = ""
    if state.get("messages"):
        last = state["messages"][-1]
        if isinstance(last, AIMessage):
            agent_msg = last.content.lower()

    guard_exit = guard == "wants_exit"
    mode_completed = mode == "completed"
    polite = any(w in agent_msg for w in ["tudo bem", "sem pressão", "qualquer momento", "fique à vontade", "tchau", "até mais"])

    passed = guard_exit and mode_completed and polite
    what = f"guard={guard} | mode={mode} | despedida educada={polite}"
    expected = "guard=wants_exit | mode=completed | despedida educada sem forçar o agendamento"
    record("A7", "'Esquece' durante agendamento", passed, what, expected)


# ═══════════════════════════════════════════════════════════════════
# A8: Qualificação → pergunta → retoma qualificação (fluxo híbrido)
# ═══════════════════════════════════════════════════════════════════
async def scenario_A8():
    print("\n" + "🔀" * 30)
    print("CENÁRIO A8: QUALIFICAÇÃO → PERGUNTA → RETOMA QUALIFICAÇÃO")
    print("🔀" * 30 + "\n")

    phone = PHONES["A8"]
    state = new_state(phone)

    state = await send_message(state, "Oi")
    state = await send_message(state, "Quero agendar uma reunião")
    state = await send_message(state, "Paulo Henrique")
    state = await send_message(state, "paulo@clinica.com")
    # Pergunta no meio
    state = await send_message(state, "Mas antes, vocês trabalham com Google Ads?")

    guard_q = state.get("interrupt_intent")
    mode_q = state.get("conversation_mode")
    agent_q = ""
    if state.get("messages"):
        last = state["messages"][-1]
        if isinstance(last, AIMessage):
            agent_q = last.content.lower()

    guard_detected_question = guard_q == "wants_question"
    answered_google = any(w in agent_q for w in ["google", "ads", "tráfego", "tráfico", "pago", "campanhas", "sim", "trabalhamos", "atendemos"])

    # Retoma qualificação após a pergunta
    state = await send_message(state, "Clínica Paulo Henrique")
    state = await send_message(state, "Clínica médica")
    state = await send_message(state, "Preciso de mais pacientes")
    state = await send_message(state, "9 mil")

    final_mode = state.get("conversation_mode")
    client_data = state.get("client_data", {})
    has_company = bool(client_data.get("company_name"))
    qualif_complete = state.get("qualification_complete", False) or state.get("budget_qualified") is not None

    passed = guard_detected_question and answered_google and (qualif_complete or has_company)
    what = (
        f"guard pergunta={guard_detected_question} ({guard_q}) | "
        f"respondeu Google={answered_google} | "
        f"retomou qualif={qualif_complete} | "
        f"mode_final={final_mode}"
    )
    expected = "guard=wants_question | responde pergunta | depois retoma e completa qualificação"
    record("A8", "Qualificação → pergunta → retoma", passed, what, expected)


# ═══════════════════════════════════════════════════════════════════
# RELATÓRIO
# ═══════════════════════════════════════════════════════════════════

def print_report():
    print("\n\n" + "=" * 70)
    print("📊 RELATÓRIO — CENÁRIOS ADVERSARIAIS (COM GUARD)")
    print("=" * 70 + "\n")

    passed_count = sum(1 for r in results if r[2])
    failed_count = sum(1 for r in results if not r[2])

    for key, name, passed, what, expected in results:
        status = "✅" if passed else "❌"
        print(f"  {status} Cenário {key}: {name}")
        if not passed:
            print(f"       Esperado:    {expected}")
            print(f"       O que houve: {what}")

    print(f"\n  TOTAL: {len(results)} cenários | ✅ {passed_count} passaram | ❌ {failed_count} falharam")
    rate = round(passed_count / len(results) * 100) if results else 0
    print(f"  TAXA: {rate}% de sucesso")
    if failed_count == 0:
        print("  🏆 TODOS OS CENÁRIOS ADVERSARIAIS PASSARAM!")
    else:
        print(f"  ⚠️  {failed_count} CENÁRIO(S) PRECISAM DE AJUSTE")

    print("\n" + "=" * 70 + "\n")


async def main():
    print("\n" + "🛡️ " * 35)
    print("SIMULAÇÃO ADVERSARIAL — INTENT GUARD")
    print(f"Data: {datetime.now(BRAZIL_TZ).strftime('%d/%m/%Y %H:%M')}")
    print("Grafo: COM GUARD (graph_with_guard.py)")
    print("🛡️ " * 35 + "\n")

    print("🧹 Limpando dados adversariais anteriores...")
    await cleanup()

    scenarios = [
        ("A1", scenario_A1),
        ("A2", scenario_A2),
        ("A3", scenario_A3),
        ("A4", scenario_A4),
        ("A5", scenario_A5),
        ("A6", scenario_A6),
        ("A7", scenario_A7),
        ("A8", scenario_A8),
    ]

    for key, fn in scenarios:
        try:
            await fn()
        except Exception as e:
            print(f"\n❌ ERRO NO CENÁRIO {key}: {e}")
            import traceback
            traceback.print_exc()
            results.append((key, fn.__name__, False, str(e), "sem crash"))
        await asyncio.sleep(0.5)

    print_report()

    print("🧹 Limpando dados adversariais...")
    await cleanup()


if __name__ == "__main__":
    asyncio.run(main())
