"""
compare_graphs.py

Roda os mesmos 20 cenários do simulate_all_flows.py com os dois grafos
(original e com Intent Guard) e exibe uma tabela comparativa de resultados.

Uso: python compare_graphs.py
"""

import asyncio
import sys
import uuid
from pathlib import Path
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from decimal import Decimal

# Carrega .env ANTES de qualquer import do app
from dotenv import load_dotenv
_env_path = Path(__file__).parent.parent / ".env"
load_dotenv(str(_env_path))

backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from langchain_core.messages import HumanMessage, AIMessage
from app.core.database import AsyncSessionLocal
from app.models.client import Client
from app.models.appointment import Appointment, AppointmentStatus
from app.schemas.clientSchema import ClientCreate, ClientSegment
from app.services.clientService import create_client
from app.services.appointmentService import create_appointment, WEEKLY_SCHEDULE, SLOT_INTERVAL
from app.schemas.appointmentSchema import AppointmentCreate
from sqlalchemy import text

# ─── Importa os dois grafos ────────────────────────────────────────────────
from app.agent.graph import marketing_crm_graph as GRAPH_ORIGINAL
from app.agent.graph_with_guard import marketing_crm_graph_guarded as GRAPH_GUARD

BRAZIL_TZ = ZoneInfo("America/Sao_Paulo")

# Telefones únicos por cenário × grafo (evitar conflito)
# Série 1xx = grafo original | Série 2xx = grafo com guard
PHONES_ORIG = {i: f"7190010{i:04d}" for i in range(1, 21)}
PHONES_GUARD = {i: f"7190020{i:04d}" for i in range(1, 21)}


# ──────────────────────────────────────────────────────────────────────────
# UTILIDADES
# ──────────────────────────────────────────────────────────────────────────

def new_state(phone: str) -> dict:
    return {
        "messages": [],
        "session_id": f"test-{phone}",
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


async def send(state: dict, message: str, graph, silent: bool = False) -> dict:
    state["messages"].append(HumanMessage(content=message))
    try:
        result = await graph.ainvoke(state)
        if not silent:
            agent_response = ""
            if result.get("messages"):
                last = result["messages"][-1]
                if isinstance(last, AIMessage):
                    agent_response = last.content
            display = (agent_response[:120] + "...") if len(agent_response) > 120 else agent_response
            print(f"    👤 {message}")
            print(f"    🤖 {display}")
            print(f"       mode={result.get('conversation_mode')} step={result.get('current_step')}")
        return result
    except Exception as e:
        if not silent:
            print(f"    ❌ ERRO: {e}")
        return state


async def cleanup():
    async with AsyncSessionLocal() as db:
        all_phones = list(PHONES_ORIG.values()) + list(PHONES_GUARD.values()) + ["7190010099", "7190020099"]
        for p in all_phones:
            await db.execute(text(f"DELETE FROM appointments WHERE client_id IN (SELECT id FROM clients WHERE phone = '{p}')"))
            await db.execute(text(f"DELETE FROM clients WHERE phone = '{p}'"))
        await db.commit()


async def mk_client(phone, first_name, company, budget, segment=ClientSegment.CLINICA_ODONTOLOGICA):
    async with AsyncSessionLocal() as db:
        data = ClientCreate(
            first_name=first_name, last_name="Teste", phone=phone,
            company_name=company, segment=segment,
            monthly_budget=Decimal(str(budget)),
            main_marketing_problem="Teste comparação"
        )
        client = await create_client(data, db)
        return str(client.id)


async def mk_appointment(client_id, hours=48, slot_index=0):
    from uuid import UUID
    base = datetime.now(BRAZIL_TZ) + timedelta(hours=hours)
    scheduled_at = None
    for d in range(14):
        candidate = base + timedelta(days=d)
        wd = candidate.weekday()
        if wd in WEEKLY_SCHEDULE and WEEKLY_SCHEDULE[wd]:
            slots = []
            for sh, sm, eh, em in WEEKLY_SCHEDULE[wd]:
                t = candidate.replace(hour=sh, minute=sm, second=0, microsecond=0)
                e = candidate.replace(hour=eh, minute=em, second=0, microsecond=0)
                while t + timedelta(minutes=30) <= e:
                    slots.append(t)
                    t += timedelta(minutes=SLOT_INTERVAL)
            if slots:
                scheduled_at = slots[min(slot_index, len(slots)-1)]
                break
    if not scheduled_at:
        scheduled_at = base.replace(hour=9, minute=0, second=0, microsecond=0)
    async with AsyncSessionLocal() as db:
        apt = await create_appointment(AppointmentCreate(
            client_id=UUID(client_id), scheduled_at=scheduled_at,
            duration_minutes=30, meeting_type="CONSULTORIA_INICIAL", notes="Teste comparação"
        ), db)
        return str(apt.id)


async def mk_appointment_expired(client_id, days_ago=7):
    from uuid import UUID
    scheduled_at = (datetime.now(BRAZIL_TZ) - timedelta(days=days_ago)).replace(hour=14, minute=0, second=0, microsecond=0)
    async with AsyncSessionLocal() as db:
        apt = Appointment(
            id=uuid.uuid4(), client_id=UUID(client_id),
            scheduled_at=scheduled_at, duration_minutes=30,
            meeting_type="CONSULTORIA_INICIAL", status=AppointmentStatus.PENDING,
            notes="Expirado — comparação"
        )
        db.add(apt)
        await db.commit()
        return str(apt.id)


# ──────────────────────────────────────────────────────────────────────────
# CENÁRIOS — cada função recebe (phone, graph) e retorna (passed, details)
# ──────────────────────────────────────────────────────────────────────────

async def cenario_01(phone, graph):
    """Fluxo feliz — agendamento completo"""
    s = new_state(phone)
    s = await send(s, "Oi", graph)
    s = await send(s, "Sim, pode falar", graph)
    s = await send(s, "Tenho uma clínica odontológica", graph)
    s = await send(s, "Clínica Sorriso Pleno", graph)
    s = await send(s, "Doutor João Silva", graph)
    s = await send(s, "Meu problema é atrair novos pacientes", graph)
    s = await send(s, "Invisto cerca de R$ 3.000 por mês em marketing", graph)
    s = await send(s, "Sim, quero agendar uma reunião", graph)

    next_tuesday = datetime.now(BRAZIL_TZ)
    while next_tuesday.weekday() != 1:
        next_tuesday += timedelta(days=1)
    next_tuesday += timedelta(weeks=1)
    date_str = next_tuesday.strftime("%d/%m/%Y")
    s = await send(s, f"Pode ser {date_str}", graph)
    s = await send(s, "9:00", graph)

    mode = s.get("conversation_mode", "")
    budget_ok = s.get("budget_qualified")
    client_id = s.get("client_id")
    passed = mode in ("scheduling", "completed") and bool(budget_ok) and bool(client_id)
    return passed, f"mode={mode} budget_qualified={budget_ok} client_id={bool(client_id)}"


async def cenario_02(phone, graph):
    """Budget reprovado → fallback"""
    s = new_state(phone)
    s = await send(s, "Oi, tudo bem", graph)
    s = await send(s, "Sim", graph)
    s = await send(s, "Sou autônomo, faço design", graph)
    s = await send(s, "Nick Design", graph)
    s = await send(s, "Nick", graph)
    s = await send(s, "Não tenho muitos clientes", graph)
    s = await send(s, "Invisto uns R$ 200 por mês", graph)
    mode = s.get("conversation_mode")
    passed = mode == "completed"
    return passed, f"budget_qualified={s.get('budget_qualified')} mode={mode}"


async def cenario_03(phone, graph):
    """Budget aprovado mas não quer agendar → thankyou"""
    s = new_state(phone)
    s = await send(s, "Olá", graph)
    s = await send(s, "Pode falar", graph)
    s = await send(s, "Trabalho com advocacia empresarial", graph)
    s = await send(s, "Escritório Mendes Advogados", graph)
    s = await send(s, "Dr. Mendes", graph)
    s = await send(s, "Quero mais clientes corporativos", graph)
    s = await send(s, "Invisto R$ 5.000 por mês", graph)
    s = await send(s, "Não, obrigado, não quero agendar agora", graph)
    mode = s.get("conversation_mode")
    passed = mode == "completed"
    return passed, f"wants_to_schedule={s.get('wants_to_schedule')} mode={mode}"


async def cenario_04(phone, graph):
    """Começa com pergunta → question_answerer → qualificação"""
    s = new_state(phone)
    s = await send(s, "Olá, vocês trabalham com Instagram?", graph)
    mode_q = s.get("conversation_mode")
    s = await send(s, "Sim, pode continuar", graph)
    mode_f = s.get("conversation_mode")
    passed = s.get("qualification_complete", False) or s.get("budget_qualified") is not None
    return passed, f"qualification_complete={s.get('qualification_complete')} budget_qualified={s.get('budget_qualified')}"


async def cenario_05(phone, graph):
    """Respostas vagas na qualificação"""
    s = new_state(phone)
    s = await send(s, "Oi", graph)
    s = await send(s, "sim", graph)
    s = await send(s, "minha empresa", graph)
    s = await send(s, "ok", graph)
    s = await send(s, "é uma coisa", graph)
    s = await send(s, "não sei dizer", graph)
    s = await send(s, "uns 5 conto", graph)
    client_data = s.get("client_data", {})
    has_name = bool(client_data.get("first_name"))
    passed = has_name
    return passed, f"first_name={client_data.get('first_name')} company={client_data.get('company_name')}"


async def cenario_06(phone, graph):
    """Muda de assunto no meio da qualificação"""
    s = new_state(phone)
    s = await send(s, "Oi", graph)
    s = await send(s, "Quero uma reunião", graph)
    s = await send(s, "Lucas Almeida", graph)
    s = await send(s, "lucas@empresa.com", graph)
    s = await send(s, "quanto custa o serviço de vocês?", graph)  # Muda de assunto
    s = await send(s, "Clínica Almeida", graph)  # Volta pro fluxo
    s = await send(s, "Clínica médica", graph)
    s = await send(s, "mas vocês atendem clínicas médicas?", graph)  # Muda de assunto
    s = await send(s, "Preciso de mais clientes", graph)
    s = await send(s, "7 mil por mês", graph)
    client_data = s.get("client_data", {})
    passed = bool(client_data.get("first_name"))
    return passed, f"Dados coletados: {list(client_data.keys())}"


async def cenario_07(phone, graph):
    """Dados confusos — emoji, gírias, valores"""
    s = new_state(phone)
    s = await send(s, "👋 eai", graph)
    s = await send(s, "sim vai", graph)
    s = await send(s, "sou dentista msm", graph)
    s = await send(s, "Dent+", graph)
    s = await send(s, "Dr. Caio", graph)
    s = await send(s, "paciente sumindo kkkk", graph)
    s = await send(s, "mto pouco, umas 3 coisas por mês", graph)
    client_data = s.get("client_data", {})
    passed = bool(client_data.get("first_name"))
    return passed, f"first_name={client_data.get('first_name')} budget={client_data.get('monthly_budget')}"


async def cenario_08(phone, graph):
    """Cliente retornando com appointment ativo"""
    client_id = await mk_client(phone, "Ana", "Beleza Total", 4000)
    await mk_appointment(client_id, hours=72)
    s = new_state(phone)
    s["client_id"] = client_id
    s = await send(s, "Oi, eu já conversei com vocês antes", graph)
    recognized = s.get("client_id") is not None
    agent_msg = ""
    if s.get("messages"):
        last = s["messages"][-1]
        if isinstance(last, AIMessage):
            agent_msg = last.content
    has_name = "Ana" in agent_msg
    passed = recognized and has_name
    return passed, f"Reconhecida={recognized} Usou nome={has_name}"


async def cenario_09(phone, graph):
    """Remarcação"""
    client_id = await mk_client(phone, "Bruno", "Construtora BH", 8000)
    await mk_appointment(client_id, hours=48)
    s = new_state(phone)
    s["client_id"] = client_id
    s = await send(s, "Oi, preciso remarcar minha reunião", graph)
    recognized = s.get("client_id") is not None
    s = await send(s, "Pode ser semana que vem?", graph)
    agent_msg = ""
    if s.get("messages"):
        last = s["messages"][-1]
        if isinstance(last, AIMessage):
            agent_msg = last.content.lower()
    mentions = any(w in agent_msg for w in ["remarc", "reagend", "novo horário", "nova data", "horário", "quando", "data"])
    passed = recognized and mentions
    return passed, f"Reconhecido={recognized} Mencionou remarcação={mentions}"


async def cenario_10(phone, graph):
    """Cancelamento"""
    client_id = await mk_client(phone, "Carla", "Studio Carla", 6000)
    await mk_appointment(client_id, hours=96)
    s = new_state(phone)
    s["client_id"] = client_id
    s = await send(s, "Quero cancelar minha reunião", graph)
    agent_msg = ""
    if s.get("messages"):
        last = s["messages"][-1]
        if isinstance(last, AIMessage):
            agent_msg = last.content.lower()
    passed = "cancel" in agent_msg or "certeza" in agent_msg or "cancelar" in agent_msg
    return passed, f"Resposta contém referência a cancelamento: {passed}"


async def cenario_11(phone, graph):
    """Retornando sem appointment — nova reunião"""
    client_id = await mk_client(phone, "Diego", "Tech Diego", 5000)
    s = new_state(phone)
    s["client_id"] = client_id
    s = await send(s, "Oi, já conversei com vocês mas não agendei nada ainda", graph)
    recognized = s.get("client_id") is not None
    agent_msg = ""
    if s.get("messages"):
        last = s["messages"][-1]
        if isinstance(last, AIMessage):
            agent_msg = last.content
    has_name = "Diego" in agent_msg
    passed = recognized
    return passed, f"Reconhecido={recognized} Usou nome={has_name}"


async def cenario_12(phone, graph):
    """Slot ocupado → alternativos"""
    # Bloquear quarta-feira próxima às 14h (mesmo slot que o cliente vai pedir)
    today = datetime.now(BRAZIL_TZ)
    days_to_wed = (2 - today.weekday()) % 7 or 7
    next_wed = today + timedelta(days=days_to_wed)
    next_wed_14h = next_wed.replace(hour=14, minute=0, second=0, microsecond=0)
    blocker_phone = "7190010099" if PHONES_ORIG[12] == phone else "7190020099"
    blocker_id = await mk_client(blocker_phone, "Blocker", "Empresa Blocker", 5000)
    from uuid import UUID as UUIDT
    async with AsyncSessionLocal() as db:
        blocker_apt = Appointment(
            id=uuid.uuid4(), client_id=UUIDT(blocker_id),
            scheduled_at=next_wed_14h, duration_minutes=30,
            meeting_type="CONSULTORIA_INICIAL", status=AppointmentStatus.CONFIRMED,
            notes="Bloqueio cenário 12"
        )
        db.add(blocker_apt)
        await db.commit()
    wed_str = next_wed.strftime("%d/%m")
    s = new_state(phone)
    s = await send(s, "Oi", graph)
    s = await send(s, "Quero agendar uma reunião", graph)
    s = await send(s, "Camila Ferreira", graph)
    s = await send(s, "camila@clinicacamila.com", graph)
    s = await send(s, "Clínica Camila Ferreira", graph)
    s = await send(s, "Clínica estética", graph)
    s = await send(s, "Preciso vender mais online", graph)
    s = await send(s, "7 mil", graph)
    s = await send(s, "sim", graph)
    s = await send(s, f"Quarta-feira dia {wed_str} às 14h", graph)  # Horário ocupado!
    agent_msg = ""
    if s.get("messages"):
        last = s["messages"][-1]
        if isinstance(last, AIMessage):
            agent_msg = last.content.lower()
    has_alt = "alternativ" in agent_msg or "outro" in agent_msg or "disponív" in agent_msg or "horário" in agent_msg or s.get("alternative_slots")
    passed = has_alt or s.get("slot_available") is False
    return passed, f"slot_available={s.get('slot_available')} alternatives={bool(s.get('alternative_slots'))}"


async def cenario_13(phone, graph):
    """Data inválida / fim de semana"""
    s = new_state(phone)
    s = await send(s, "Oi", graph)
    s = await send(s, "Pode falar", graph)
    s = await send(s, "Trabalho com pet shop", graph)
    s = await send(s, "PetShop Feliz", graph)
    s = await send(s, "Fernanda", graph)
    s = await send(s, "Quero mais clientes", graph)
    s = await send(s, "R$ 2.500 por mês", graph)
    s = await send(s, "Sim, quero agendar", graph)
    # Encontrar próximo sábado
    next_saturday = datetime.now(BRAZIL_TZ)
    while next_saturday.weekday() != 5:
        next_saturday += timedelta(days=1)
    date_str = next_saturday.strftime("%d/%m/%Y")
    s = await send(s, date_str, graph)
    mode = s.get("conversation_mode")
    slot = s.get("slot_available")
    still_collecting = (mode == "scheduling" and slot is None)
    passed = mode in ("scheduling", "datetime_collecting") or still_collecting
    return passed, f"mode={mode} slot_available={slot} (fim de semana rejeitado corretamente)"


async def cenario_14(phone, graph):
    """Desistência no meio da qualificação"""
    s = new_state(phone)
    s = await send(s, "Oi", graph)
    s = await send(s, "sim", graph)
    s = await send(s, "tenho uma loja", graph)
    s = await send(s, "não, deixa pra lá, não tenho interesse", graph)
    agent_msg = ""
    if s.get("messages"):
        last = s["messages"][-1]
        if isinstance(last, AIMessage):
            agent_msg = last.content
    passed = bool(agent_msg)
    return passed, f"Resposta recebida: {bool(agent_msg)} mode={s.get('conversation_mode')}"


async def cenario_15(phone, graph):
    """Mensagens fora de contexto (nonsense)"""
    s = new_state(phone)
    s = await send(s, "🔥🔥🔥", graph)
    s = await send(s, "asdfghjkl", graph)
    s = await send(s, "???", graph)
    agent_msg = ""
    if s.get("messages"):
        last = s["messages"][-1]
        if isinstance(last, AIMessage):
            agent_msg = last.content
    passed = bool(agent_msg)
    return passed, f"Agente respondeu sem crash: {passed}"


async def cenario_16(phone, graph):
    """Appointment expirado → auto NO_SHOW"""
    client_id = await mk_client(phone, "Gabriel", "Gab Tech", 7000)
    await mk_appointment_expired(client_id, days_ago=7)
    s = new_state(phone)
    s["client_id"] = client_id
    s = await send(s, "Oi", graph)
    mode = s.get("conversation_mode")
    agent_msg = ""
    if s.get("messages"):
        last = s["messages"][-1]
        if isinstance(last, AIMessage):
            agent_msg = last.content
    # Verificar no banco: appointment deve ser NO_SHOW
    from uuid import UUID as UUIDT
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select as sa_select
        result = await db.execute(
            sa_select(Appointment).where(Appointment.client_id == UUIDT(client_id))
        )
        apts = result.scalars().all()
        is_no_show = any(a.status == AppointmentStatus.NO_SHOW for a in apts)
    passed = is_no_show and mode != "returning_with_appointment"
    return passed, f"NO_SHOW={is_no_show} mode={mode} Usou nome={'Gabriel' in agent_msg}"


async def cenario_17(phone, graph):
    """Cancelamento completo — 2 etapas"""
    client_id = await mk_client(phone, "Helena", "H Beauty", 4500)
    await mk_appointment(client_id, hours=120)
    s = new_state(phone)
    s["client_id"] = client_id
    s = await send(s, "Quero cancelar", graph)
    agent_msg1 = ""
    if s.get("messages"):
        last = s["messages"][-1]
        if isinstance(last, AIMessage):
            agent_msg1 = last.content.lower()
    asked = "certeza" in agent_msg1 or "cancelar" in agent_msg1 or "confirma" in agent_msg1
    s = await send(s, "Sim, pode cancelar", graph)
    agent_msg2 = ""
    if s.get("messages"):
        last = s["messages"][-1]
        if isinstance(last, AIMessage):
            agent_msg2 = last.content.lower()
    # Verificar banco
    from uuid import UUID as UUIDT
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select as sa_select
        result = await db.execute(
            sa_select(Appointment).where(Appointment.client_id == UUIDT(client_id))
        )
        apts = result.scalars().all()
        is_cancelled = any(a.status == AppointmentStatus.CANCELLED for a in apts)
    confirmed = "cancelad" in agent_msg2 or "pronto" in agent_msg2 or "feito" in agent_msg2
    passed = asked and is_cancelled and confirmed
    return passed, f"Pediu confirmação={asked} DB_CANCELLED={is_cancelled} Agente_confirmou={confirmed}"


async def cenario_18(phone, graph):
    """Escolha de slot alternativo"""
    client_id = await mk_client(phone, "Igor", "Igor Soluções", 6000)
    s = new_state(phone)
    s = await send(s, "Oi", graph)
    s = await send(s, "Pode falar", graph)
    s = await send(s, "Consultoria financeira", graph)
    s = await send(s, "Finance Pro", graph)
    s = await send(s, "Igor", graph)
    s = await send(s, "Preciso de mais clientes corporativos", graph)
    s = await send(s, "R$ 4.000 por mês", graph)
    s = await send(s, "Sim, quero agendar", graph)
    next_tuesday = datetime.now(BRAZIL_TZ)
    while next_tuesday.weekday() != 1:
        next_tuesday += timedelta(days=1)
    next_tuesday += timedelta(weeks=1)
    date_str = next_tuesday.strftime("%d/%m/%Y")
    s = await send(s, date_str, graph)
    s = await send(s, "9:00", graph)
    pre_msg = ""
    if s.get("messages"):
        last = s["messages"][-1]
        if isinstance(last, AIMessage):
            pre_msg = last.content.lower()
    has_alts = "1)" in pre_msg or "2)" in pre_msg or s.get("alternative_slots")
    if has_alts:
        s = await send(s, "1", graph)
    final_msg = ""
    if s.get("messages"):
        last = s["messages"][-1]
        if isinstance(last, AIMessage):
            final_msg = last.content.lower()
    chose = s.get("chosen_slot") is not None
    confirmed = s.get("appointment_confirmed", False)
    progressed = "confirmad" in final_msg or "agendad" in final_msg or chose or confirmed
    passed = has_alts and progressed
    return passed, f"Alternativas={has_alts} chose_slot={chose} appointment_confirmed={confirmed}"


async def cenario_19(phone, graph):
    """Cliente diz 'essa data já passou'"""
    client_id = await mk_client(phone, "Julia", "J Moda", 5500)
    await mk_appointment_expired(client_id, days_ago=3)
    s = new_state(phone)
    s["client_id"] = client_id
    s = await send(s, "Oi, eu agendei uma reunião mas acho que a data já passou", graph)
    mode = s.get("conversation_mode")
    agent_msg = ""
    if s.get("messages"):
        last = s["messages"][-1]
        if isinstance(last, AIMessage):
            agent_msg = last.content
    date_ago = (datetime.now(BRAZIL_TZ) - timedelta(days=3)).strftime("%d/%m")
    mentions_expired = date_ago in agent_msg
    passed = mode != "returning_with_appointment" and not mentions_expired
    return passed, f"mode={mode} Menciona data expirada={mentions_expired}"


async def cenario_20(phone, graph):
    """Reagendamento completo"""
    client_id = await mk_client(phone, "Lucas", "Clínica Lucas Fisio", 7000)
    await mk_appointment(client_id, hours=240, slot_index=0)
    s = new_state(phone)
    s["client_id"] = client_id
    s = await send(s, "Oi, preciso remarcar minha reunião", graph)
    agent_msg1 = ""
    if s.get("messages"):
        last = s["messages"][-1]
        if isinstance(last, AIMessage):
            agent_msg1 = last.content.lower()
    understood = any(w in agent_msg1 for w in ["remarc", "reagend", "qual", "data", "horário", "quando"])
    mode_sched = s.get("conversation_mode") == "scheduling"
    # Enviar novo horário: sexta que vem
    today = datetime.now(BRAZIL_TZ)
    days_to_fri = (4 - today.weekday()) % 7 or 7
    next_fri = today + timedelta(days=days_to_fri)
    fri_str = next_fri.strftime("%d/%m")
    if understood or mode_sched:
        s = await send(s, f"Sexta dia {fri_str} às 9h", graph)
    final_msg = ""
    if s.get("messages"):
        last = s["messages"][-1]
        if isinstance(last, AIMessage):
            final_msg = last.content.lower()
    progressed = any(w in final_msg for w in ["confirmad", "agendad", "marcad", "disponív", "horário", "sexta", "09:00", "9h", "9:00", fri_str])
    passed = (understood or mode_sched) and progressed
    return passed, f"Entendeu remarcação={understood} mode_scheduling={mode_sched} Progrediu={progressed}"


# ──────────────────────────────────────────────────────────────────────────
# RUNNER — executa um grafo e coleta resultados
# ──────────────────────────────────────────────────────────────────────────

SCENARIOS = [
    (1,  cenario_01, "Fluxo feliz — agendamento completo"),
    (2,  cenario_02, "Budget reprovado → fallback"),
    (3,  cenario_03, "Não quer agendar → thankyou"),
    (4,  cenario_04, "Começa com pergunta → qualificação"),
    (5,  cenario_05, "Respostas vagas"),
    (6,  cenario_06, "Muda de assunto na qualificação"),
    (7,  cenario_07, "Dados confusos / gírias"),
    (8,  cenario_08, "Retornando com appointment"),
    (9,  cenario_09, "Remarcação"),
    (10, cenario_10, "Cancelamento"),
    (11, cenario_11, "Retornando sem appointment"),
    (12, cenario_12, "Slot ocupado → alternativos"),
    (13, cenario_13, "Data inválida / fim de semana"),
    (14, cenario_14, "Desistência na qualificação"),
    (15, cenario_15, "Nonsense / fora de contexto"),
    (16, cenario_16, "Appointment expirado → NO_SHOW"),
    (17, cenario_17, "Cancelamento completo 2 etapas"),
    (18, cenario_18, "Escolha de slot alternativo"),
    (19, cenario_19, "Data expirada detectada"),
    (20, cenario_20, "Reagendamento completo"),
]


async def run_all(graph, phones: dict, label: str) -> list[tuple[int, bool, str]]:
    """Executa todos os 20 cenários com o grafo indicado."""
    results = []
    print(f"\n{'═'*70}")
    print(f"  RODANDO: {label}")
    print(f"{'═'*70}\n")
    for num, fn, name in SCENARIOS:
        print(f"── Cenário {num:02d}: {name} ──")
        try:
            passed, details = await fn(phones[num], graph)
        except Exception as e:
            import traceback
            traceback.print_exc()
            passed, details = False, f"EXCEÇÃO: {e}"
        icon = "✅" if passed else "❌"
        print(f"  {icon} {'PASSOU' if passed else 'FALHOU'} | {details}\n")
        results.append((num, passed, details))
        await asyncio.sleep(0.3)
    return results


# ──────────────────────────────────────────────────────────────────────────
# RELATÓRIO COMPARATIVO
# ──────────────────────────────────────────────────────────────────────────

def print_comparison(orig: list, guard: list):
    print(f"\n\n{'═'*80}")
    print("  TABELA COMPARATIVA: GRAFO ORIGINAL  ×  GRAFO COM INTENT GUARD")
    print(f"{'═'*80}")
    print(f"  {'#':>2}  {'CENÁRIO':<40} {'ORIGINAL':^10} {'GUARD':^10} {'DIFF':^6}")
    print(f"  {'─'*2}  {'─'*40} {'─'*10} {'─'*10} {'─'*6}")

    changed = []
    for (num, p_orig, d_orig), (_, p_guard, d_guard) in zip(orig, guard):
        _, _, name = SCENARIOS[num - 1]
        o_icon = "✅" if p_orig else "❌"
        g_icon = "✅" if p_guard else "❌"
        if p_orig != p_guard:
            diff = "⚠️ DIFF"
            changed.append((num, name, p_orig, p_guard, d_orig, d_guard))
        else:
            diff = "  ─  "
        print(f"  {num:>2}  {name:<40} {o_icon:^10} {g_icon:^10} {diff:^6}")

    total_orig  = sum(1 for _, p, _ in orig  if p)
    total_guard = sum(1 for _, p, _ in guard if p)
    total = len(orig)

    print(f"  {'─'*70}")
    print(f"  {'TOTAL':<44} {total_orig}/{total}     {total_guard}/{total}")
    print(f"  {'TAXA':<44} {total_orig/total*100:.0f}%        {total_guard/total*100:.0f}%")
    print(f"{'═'*80}\n")

    if changed:
        print(f"  ⚠️  CENÁRIOS COM RESULTADO DIFERENTE ({len(changed)}):\n")
        for num, name, p_o, p_g, d_o, d_g in changed:
            print(f"  Cenário {num} — {name}")
            print(f"    Original ({('✅' if p_o else '❌')}): {d_o}")
            print(f"    Guard    ({('✅' if p_g else '❌')}): {d_g}")
            print()
    else:
        print("  ✅ Nenhuma diferença de resultado entre os dois grafos.\n")


# ──────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────

async def main():
    print("\n" + "🔬" * 35)
    print("COMPARAÇÃO: GRAFO ORIGINAL  ×  GRAFO COM INTENT GUARD")
    print(f"Data: {datetime.now(BRAZIL_TZ).strftime('%d/%m/%Y %H:%M')}")
    print("🔬" * 35)

    print("\n🧹 Limpando dados de testes anteriores...")
    await cleanup()
    print("✅ Banco limpo\n")

    orig_results  = await run_all(GRAPH_ORIGINAL, PHONES_ORIG,  "GRAFO ORIGINAL")
    guard_results = await run_all(GRAPH_GUARD,    PHONES_GUARD, "GRAFO COM INTENT GUARD")

    print_comparison(orig_results, guard_results)


if __name__ == "__main__":
    asyncio.run(main())
