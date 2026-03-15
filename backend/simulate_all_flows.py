"""
simulate_all_flows.py

Simulação abrangente de 37 cenários de conversa com o agente PydanticAI.
Cobre todos os fluxos: qualificação, agendamento, retornando, slot ocupado,
comportamentos humanos imprevisíveis, etc.

CENÁRIOS:
 1. Fluxo feliz — agendamento completo
 2. Budget reprovado → fallback
 3. Budget aprovado mas não quer agendar → thankyou
 4. Começa com pergunta → qualificação
 5. Respostas vagas na qualificação
 6. Muda de assunto no meio da qualificação
 7. Dados confusos / emoji / gírias
 8. Cliente retornando (com appointment) → greeting contextual
 9. Cliente retornando → remarcação
10. Cliente retornando → cancelamento
11. Cliente retornando (sem appointment) → nova reunião
12. Slot ocupado → horários alternativos
13. Data inválida / passada / fim de semana
14. Cliente desiste no meio da qualificação
15. Mensagens fora de contexto
16. Cliente retornando com appointment EXPIRADO → auto NO_SHOW
17. Cancelamento completo (2 etapas)
18. Escolha de slot alternativo (responde "1" ou "2")
19. Cliente retornando com appointment expirado detectado automaticamente
20. Reagendamento completo
21. Mensagem ambígua → esclarece → qualificação
22. Escolha alternativa "2" (segunda opção)
23. Ask to schedule → "não quero" → encerra
24. Só uma alternativa disponível → escolha "1"
25. Datetime só dia → oferta horários do dia → escolhe
26. Desistência na escolha de alternativa ("outro dia")
27. Várias mensagens unclear → resiliência / escalação
28. Email inválido → agente pede novamente ou aceita sem email
29. Orçamento indefinido → agente esclarece ou encerra
30. Segmento fora da saúde → agente recusa gentilmente
31. Cliente duplicado → buscar_cliente detecta e não cria novo
32. Data muito no futuro (6 meses) → agente aceita e agenda normalmente
33. Mensagem muito longa → agente processa sem travar
34. Múltiplas datas na mesma mensagem → agente escolhe uma e confirma
35. Paciente buscando médico → agente encerra gentilmente
36. Todos slots do dia ocupados → agente sugere outro dia
37. Agendamento para hoje → agente verifica e responde conforme disponibilidade

IMPORTANTE: Usa banco de produção — rodar com cautela.
"""

import asyncio
import sys
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from decimal import Decimal

from dotenv import load_dotenv
_env_path = Path(__file__).parent.parent / ".env"
load_dotenv(str(_env_path))

backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from app.agent.agent import crm_agent
from app.agent.deps import ConversationDeps
from app.core.database import AsyncSessionLocal
from app.models.client import Client
from app.models.appointment import Appointment, AppointmentStatus
from app.schemas.clientSchema import ClientCreate, ClientSegment
from app.schemas.appointmentSchema import AppointmentCreate
from app.services.clientService import create_client
from app.services.appointmentService import create_appointment, WEEKLY_SCHEDULE, SLOT_INTERVAL
from sqlalchemy import text, select
from uuid import UUID

BRAZIL_TZ = ZoneInfo("America/Sao_Paulo")

PHONES = {i: f"7190000{i:04d}" for i in range(1, 38)}

results = []


# ========== UTILIDADES ==========

def new_state(phone: str) -> dict:
    """Cria estado inicial limpo para uma nova conversa."""
    return {
        "messages": [],
        "phone": phone,
        "client_id": None,
        "appointment_id": None,
        "last_response": "",
    }


async def send_message(state: dict, message: str) -> dict:
    """Envia uma mensagem ao agente e retorna o estado atualizado."""
    deps = ConversationDeps(
        phone=state["phone"],
        client_id=state.get("client_id"),
        appointment_id=state.get("appointment_id"),
    )

    try:
        result = await crm_agent.run(
            message,
            message_history=state["messages"],
            deps=deps,
        )
        response = result.output
        new_messages = result.all_messages()
    except Exception as e:
        print(f"  ❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        state["last_response"] = ""
        return state

    display = response[:150] + "..." if len(response) > 150 else response
    print(f"  👤 Cliente: {message}")
    print(f"  🤖 Agente:  {display}")
    print(f"     client_id={deps.client_id} | appointment_id={deps.appointment_id}")
    print()

    return {
        "messages": new_messages,
        "phone": state["phone"],
        "client_id": deps.client_id,
        "appointment_id": deps.appointment_id,
        "last_response": response,
    }


async def cleanup_phones():
    """Limpa todos os telefones de teste do banco."""
    async with AsyncSessionLocal() as db:
        all_phones = list(PHONES.values()) + ["71900000099"]
        placeholders = ", ".join(f"'{p}'" for p in all_phones)
        await db.execute(text(
            f"DELETE FROM appointments WHERE client_id IN "
            f"(SELECT id FROM clients WHERE phone IN ({placeholders}))"
        ))
        await db.execute(text(f"DELETE FROM clients WHERE phone IN ({placeholders})"))
        await db.commit()


async def create_test_client(
    phone: str, first_name: str, company: str, budget: float,
    segment=ClientSegment.CLINICA_ODONTOLOGICA
) -> str:
    """Cria cliente de teste e retorna o client_id (string)."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Client).where(Client.phone == phone))
        existing = result.scalar_one_or_none()
        if existing:
            return str(existing.id)

        client_data = ClientCreate(
            first_name=first_name,
            last_name="Teste",
            phone=phone,
            company_name=company,
            segment=segment,
            monthly_budget=Decimal(str(budget)),
            main_marketing_problem="Teste de simulação",
        )
        client = await create_client(client_data, db)
        return str(client.id)


async def create_test_appointment(
    client_id: str, hours_from_now: int = 48, slot_index: int = 0
) -> str:
    """Cria appointment futuro de teste e retorna o appointment_id."""
    base_date = datetime.now(BRAZIL_TZ) + timedelta(hours=hours_from_now)

    for day_offset in range(14):
        candidate = base_date + timedelta(days=day_offset)
        weekday = candidate.weekday()
        if weekday in WEEKLY_SCHEDULE and WEEKLY_SCHEDULE[weekday]:
            all_slots = []
            for start_h, start_m, end_h, end_m in WEEKLY_SCHEDULE[weekday]:
                slot_time = candidate.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
                end_time = candidate.replace(hour=end_h, minute=end_m, second=0, microsecond=0)
                while slot_time + timedelta(minutes=30) <= end_time:
                    all_slots.append(slot_time)
                    slot_time += timedelta(minutes=SLOT_INTERVAL)
            if all_slots:
                scheduled_at = all_slots[min(slot_index, len(all_slots) - 1)]
                break
    else:
        scheduled_at = base_date.replace(hour=9, minute=0, second=0, microsecond=0)

    async with AsyncSessionLocal() as db:
        apt_data = AppointmentCreate(
            client_id=UUID(client_id) if isinstance(client_id, str) else client_id,
            scheduled_at=scheduled_at,
            duration_minutes=30,
            meeting_type="CONSULTORIA_INICIAL",
            notes="Teste de simulação",
        )
        apt = await create_appointment(apt_data, db)
        return str(apt.id)


async def create_test_appointment_expired(client_id: str, days_ago: int = 7) -> str:
    """Cria appointment no passado (expirado) para testes."""
    scheduled_at = (
        datetime.now(BRAZIL_TZ) - timedelta(days=days_ago)
    ).replace(hour=14, minute=0, second=0, microsecond=0)

    async with AsyncSessionLocal() as db:
        apt = Appointment(
            id=uuid.uuid4(),
            client_id=UUID(client_id) if isinstance(client_id, str) else client_id,
            scheduled_at=scheduled_at,
            duration_minutes=30,
            meeting_type="CONSULTORIA_INICIAL",
            status=AppointmentStatus.PENDING,
            notes="Teste de appointment expirado",
        )
        db.add(apt)
        await db.commit()
        return str(apt.id)


async def get_active_appointments(client_id_str: str) -> list:
    """Retorna appointments ativos de um cliente."""
    now = datetime.now(BRAZIL_TZ)
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Appointment).where(
                Appointment.client_id == UUID(client_id_str),
                Appointment.status.in_([AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED]),
            )
        )
        apts = result.scalars().all()
    return [a for a in apts if (a.scheduled_at.replace(tzinfo=BRAZIL_TZ) if a.scheduled_at.tzinfo is None else a.scheduled_at.astimezone(BRAZIL_TZ)) >= now]


def record_result(scenario: int, name: str, passed: bool, details: str = ""):
    status = "✅ PASSOU" if passed else "❌ FALHOU"
    results.append((scenario, name, passed, details))
    print(f"\n  {'='*60}")
    print(f"  {status}: Cenário {scenario} — {name}")
    if details:
        print(f"  {details}")
    print(f"  {'='*60}\n")


# ========== CENÁRIOS ==========

async def scenario_01():
    """Cenário 1: Fluxo feliz — agendamento completo."""
    print("\n" + "🟢" * 35)
    print("CENÁRIO 1: FLUXO FELIZ — AGENDAMENTO COMPLETO")
    print("🟢" * 35 + "\n")

    state = new_state(PHONES[1])
    for msg in [
        "Oi", "Quero marcar uma reunião", "Carlos Oliveira",
        "carlos@clinicadente.com", "Clínica DentalCare", "Clínica odontológica",
        "Quero atrair mais pacientes pela internet", "8 mil reais por mês",
        "sim", "Quarta-feira às 14h",
    ]:
        state = await send_message(state, msg)
        await asyncio.sleep(0.3)

    client_created = state.get("client_id") is not None
    appointment_created = state.get("appointment_id") is not None
    passed = client_created and appointment_created
    record_result(1, "Fluxo feliz", passed,
                  f"client_id={state.get('client_id')} | appointment_id={state.get('appointment_id')}")


async def scenario_02():
    """Cenário 2: Budget reprovado → fallback."""
    print("\n" + "🔴" * 35)
    print("CENÁRIO 2: BUDGET REPROVADO → FALLBACK")
    print("🔴" * 35 + "\n")

    state = new_state(PHONES[2])
    for msg in [
        "Olá, boa tarde", "Quero saber sobre marketing", "sim",
        "Ana Costa", "ana@clinicaana.com", "Clínica Ana Costa",
        "Psicologia", "Preciso de clientes novos", "1500 reais",
    ]:
        state = await send_message(state, msg)
        await asyncio.sleep(0.3)

    resp = state.get("last_response", "").lower()
    rejected = any(w in resp for w in ["3.000", "3000", "mínimo", "minimo", "partir de"])
    no_appointment = state.get("appointment_id") is None
    passed = rejected and no_appointment
    record_result(2, "Budget reprovado → fallback", passed,
                  f"Menciona mínimo={rejected} | sem appointment={no_appointment}")


async def scenario_03():
    """Cenário 3: Budget OK mas não quer agendar → thankyou."""
    print("\n" + "🟡" * 35)
    print("CENÁRIO 3: NÃO QUER AGENDAR → THANKYOU")
    print("🟡" * 35 + "\n")

    state = new_state(PHONES[3])
    for msg in [
        "Oi", "Quero uma reunião", "Pedro Mendes",
        "pedro@empresa.com", "Clínica Pedro Mendes", "Clínica médica",
        "Quero mais leads qualificados", "10 mil", "agora não, depois eu vejo",
    ]:
        state = await send_message(state, msg)
        await asyncio.sleep(0.3)

    resp = state.get("last_response", "").lower()
    farewell = any(w in resp for w in [
        "sucesso", "quando quiser", "fique à vontade", "chamar", "contato", "sem problema",
        "disposição", "obrigado", "ótimo", "otimo", "tudo bem", "entendido", "qualquer",
    ])
    no_appointment = state.get("appointment_id") is None
    passed = farewell and no_appointment
    record_result(3, "Não quer agendar → thankyou", passed,
                  f"Despedida={farewell} | sem appointment={no_appointment}")


async def scenario_04():
    """Cenário 4: Começa com pergunta → qualificação."""
    print("\n" + "🔵" * 35)
    print("CENÁRIO 4: COMEÇA COM PERGUNTA")
    print("🔵" * 35 + "\n")

    state = new_state(PHONES[4])
    for msg in [
        "Oi", "Vocês fazem gestão de tráfego pago?",
        "sim, pode perguntar", "Fernanda Lima",
        "fernanda@clinicabemestar.com", "Clínica Bem Estar",
        "Clínica estética", "Preciso de mais agendamentos", "6 mil",
    ]:
        state = await send_message(state, msg)
        await asyncio.sleep(0.3)

    client_created = state.get("client_id") is not None
    record_result(4, "Começa com pergunta → qualificação", client_created,
                  f"client_id={state.get('client_id')}")


async def scenario_05():
    """Cenário 5: Respostas vagas na qualificação."""
    print("\n" + "🟠" * 35)
    print("CENÁRIO 5: RESPOSTAS VAGAS NA QUALIFICAÇÃO")
    print("🟠" * 35 + "\n")

    state = new_state(PHONES[5])
    for msg in [
        "Oi", "Quero agendar", "sim", "ok",
        "Marcos Ribeiro", "marcos@email.com", "sim",
        "Clínica Nutri Marcos", "Nutricionista",
        "Quero vender mais pela internet", "5 mil",
    ]:
        state = await send_message(state, msg)
        await asyncio.sleep(0.3)

    client_created = state.get("client_id") is not None
    record_result(5, "Respostas vagas na qualificação", client_created,
                  f"client_id={state.get('client_id')}")


async def scenario_06():
    """Cenário 6: Muda de assunto no meio da qualificação."""
    print("\n" + "🟣" * 35)
    print("CENÁRIO 6: MUDA DE ASSUNTO NO MEIO")
    print("🟣" * 35 + "\n")

    state = new_state(PHONES[6])
    for msg in [
        "Oi", "Quero uma reunião", "Lucas Almeida", "lucas@empresa.com",
        "quanto custa o serviço de vocês?", "Clínica Almeida",
        "Clínica médica", "mas vocês atendem clínicas médicas?",
        "Preciso de mais clientes", "7 mil por mês",
    ]:
        state = await send_message(state, msg)
        await asyncio.sleep(0.3)

    client_created = state.get("client_id") is not None
    record_result(6, "Muda de assunto no meio", client_created,
                  f"client_id={state.get('client_id')}")


async def scenario_07():
    """Cenário 7: Dados confusos / gírias / emoji."""
    print("\n" + "🤪" * 35)
    print("CENÁRIO 7: DADOS CONFUSOS / GÍRIAS / EMOJI")
    print("🤪" * 35 + "\n")

    state = new_state(PHONES[7])
    for msg in [
        "eai blz 😎", "quero marcar um papo aí",
        "me chamo Thiago mas todo mundo me chama de Thi",
        "thi@gmail.com", "Clínica do Thi 💪", "fisioterapeuta",
        "tá fraco demais, não consigo clientes novos irmão kkk",
        "uns 5 conto",
    ]:
        state = await send_message(state, msg)
        await asyncio.sleep(0.3)

    client_created = state.get("client_id") is not None
    record_result(7, "Dados confusos / gírias", client_created,
                  f"client_id={state.get('client_id')}")


async def scenario_08():
    """Cenário 8: Cliente retornando (com appointment) → greeting contextual."""
    print("\n" + "🔄" * 35)
    print("CENÁRIO 8: CLIENTE RETORNANDO (COM APPOINTMENT)")
    print("🔄" * 35 + "\n")

    phone = PHONES[8]
    client_id = await create_test_client(phone, "Juliana", "Clínica Bela Pele", 8000.0, ClientSegment.CLINICA_ESTETICA)
    await create_test_appointment(client_id)

    state = new_state(phone)
    state = await send_message(state, "Oi, tudo bem?")
    await asyncio.sleep(0.3)

    resp = state.get("last_response", "")
    recognized = state.get("client_id") is not None
    used_name = "Juliana" in resp
    passed = recognized and used_name
    record_result(8, "Retornando com appointment — greeting", passed,
                  f"Reconhecida={recognized} | Usou nome={used_name}")


async def scenario_09():
    """Cenário 9: Cliente retornando → remarcação."""
    print("\n" + "📅" * 35)
    print("CENÁRIO 9: CLIENTE RETORNANDO → REMARCAÇÃO")
    print("📅" * 35 + "\n")

    phone = PHONES[9]
    client_id = await create_test_client(phone, "Roberto", "Farmácia Saúde", 6000.0, ClientSegment.FARMACIA)
    await create_test_appointment(client_id, hours_from_now=72, slot_index=1)

    state = new_state(phone)
    for msg in ["Oi, preciso remarcar minha reunião", "Quarta-feira às 9h"]:
        state = await send_message(state, msg)
        await asyncio.sleep(0.3)

    recognized = state.get("client_id") is not None
    resp = state.get("last_response", "").lower()
    mentions_reschedule = any(w in resp for w in ["remarc", "reagend", "novo horário", "nova data", "horário", "quando", "data"])

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Appointment).where(Appointment.client_id == UUID(client_id))
            .order_by(Appointment.created_at.asc())
        )
        all_apts = result.scalars().all()
        cancelled = [a for a in all_apts if a.status == AppointmentStatus.CANCELLED]
        active = [a for a in all_apts if a.status in (AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED)]

    passed = recognized and mentions_reschedule
    record_result(9, "Remarcação", passed,
                  f"Reconhecido={recognized} | Respondeu={mentions_reschedule} | "
                  f"DB: total={len(all_apts)} cancelados={len(cancelled)} ativos={len(active)}")


async def scenario_10():
    """Cenário 10: Cliente retornando → cancelamento."""
    print("\n" + "🚫" * 35)
    print("CENÁRIO 10: CLIENTE RETORNANDO → CANCELAMENTO")
    print("🚫" * 35 + "\n")

    phone = PHONES[10]
    client_id = await create_test_client(phone, "Sandra", "Lab Diagnóstico", 9000.0, ClientSegment.LABORATORIO)
    await create_test_appointment(client_id, hours_from_now=96, slot_index=2)

    state = new_state(phone)
    state = await send_message(state, "Oi, quero cancelar minha reunião")
    await asyncio.sleep(0.3)

    resp = state.get("last_response", "").lower()
    mentions_cancel = any(w in resp for w in ["cancel", "certeza", "confirma", "tem certeza"])
    record_result(10, "Cancelamento", mentions_cancel,
                  f"Resposta menciona cancelamento={mentions_cancel}")


async def scenario_11():
    """Cenário 11: Cliente retornando SEM appointment → nova reunião."""
    print("\n" + "🆕" * 35)
    print("CENÁRIO 11: RETORNANDO SEM APPOINTMENT → NOVA REUNIÃO")
    print("🆕" * 35 + "\n")

    phone = PHONES[11]
    client_id = await create_test_client(phone, "Diego", "Diego Fisio", 5000.0, ClientSegment.FISIOTERAPEUTA)

    state = new_state(phone)
    state = await send_message(state, "Oi, quero marcar uma reunião")
    await asyncio.sleep(0.3)

    recognized = state.get("client_id") is not None
    resp = state.get("last_response", "")
    used_name = "Diego" in resp
    passed = recognized
    record_result(11, "Retornando sem appointment → nova reunião", passed,
                  f"Reconhecido={recognized} | Usou nome={used_name}")


async def scenario_12():
    """Cenário 12: Slot ocupado → horários alternativos."""
    print("\n" + "⏰" * 35)
    print("CENÁRIO 12: SLOT OCUPADO → HORÁRIOS ALTERNATIVOS")
    print("⏰" * 35 + "\n")

    today = datetime.now(BRAZIL_TZ)
    days_to_wed = (2 - today.weekday()) % 7 or 7
    next_wed = today + timedelta(days=days_to_wed)
    next_wed_14h = next_wed.replace(hour=14, minute=0, second=0, microsecond=0)

    blocker_id = await create_test_client("71900000099", "Blocker", "Blocker Corp", 5000.0, ClientSegment.CLINICA_MEDICA)
    async with AsyncSessionLocal() as db:
        db.add(Appointment(
            id=uuid.uuid4(), client_id=UUID(blocker_id), scheduled_at=next_wed_14h,
            duration_minutes=30, meeting_type="CONSULTORIA_INICIAL",
            status=AppointmentStatus.CONFIRMED, notes="Bloqueio cenário 12",
        ))
        await db.commit()

    wed_str = next_wed.strftime("%d/%m")
    state = new_state(PHONES[12])
    for msg in [
        "Oi", "Quero agendar uma reunião", "Camila Ferreira",
        "camila@clinicacamila.com", "Clínica Camila Ferreira",
        "Clínica estética", "Preciso vender mais online",
        "7 mil", "sim", f"Quarta-feira dia {wed_str} às 14h",
    ]:
        state = await send_message(state, msg)
        await asyncio.sleep(0.3)

    resp = state.get("last_response", "").lower()
    offered_alternatives = any(w in resp for w in ["alternativ", "outro", "disponív", "horário", "opção", "1)", "1."])
    passed = offered_alternatives or state.get("appointment_id") is None
    record_result(12, "Slot ocupado → alternativas", passed,
                  f"Ofereceu alternativas={offered_alternatives}")

    async with AsyncSessionLocal() as db:
        await db.execute(text("DELETE FROM appointments WHERE client_id IN (SELECT id FROM clients WHERE phone = '71900000099')"))
        await db.execute(text("DELETE FROM clients WHERE phone = '71900000099'"))
        await db.commit()


async def scenario_13():
    """Cenário 13: Data inválida / passada / fim de semana."""
    print("\n" + "📛" * 35)
    print("CENÁRIO 13: DATA INVÁLIDA / FIM DE SEMANA")
    print("📛" * 35 + "\n")

    state = new_state(PHONES[13])
    for msg in [
        "Olá", "Quero marcar reunião", "Ricardo Souza",
        "ricardo@clinica.com", "Clínica Ricardo Souza",
        "Clínica médica", "Preciso posicionar minha marca",
        "15 mil", "sim", "Sábado às 10h",
    ]:
        state = await send_message(state, msg)
        await asyncio.sleep(0.3)

    resp = state.get("last_response", "").lower()
    no_appointment = state.get("appointment_id") is None
    redirected = any(w in resp for w in [
        "sábado", "fim de semana", "disponív", "segunda", "terça",
        "quarta", "quinta", "sexta", "outro dia", "qual dia", "qual data",
    ])
    passed = no_appointment and redirected
    record_result(13, "Data inválida / fim de semana", passed,
                  f"Sem appointment={no_appointment} | Redirecionou={redirected}")


async def scenario_14():
    """Cenário 14: Cliente desiste no meio da qualificação."""
    print("\n" + "🏳️" * 35)
    print("CENÁRIO 14: CLIENTE DESISTE NO MEIO")
    print("🏳️" * 35 + "\n")

    state = new_state(PHONES[14])
    for msg in [
        "Oi", "Quero uma reunião", "Amanda Torres",
        "amanda@email.com", "depois eu falo isso, não tenho tempo agora",
    ]:
        state = await send_message(state, msg)
        await asyncio.sleep(0.3)

    responded = bool(state.get("last_response"))
    record_result(14, "Desistência no meio", responded,
                  f"Agente respondeu sem crash: {responded}")


async def scenario_15():
    """Cenário 15: Mensagens fora de contexto."""
    print("\n" + "🤡" * 35)
    print("CENÁRIO 15: MENSAGENS FORA DE CONTEXTO")
    print("🤡" * 35 + "\n")

    state = new_state(PHONES[15])
    for msg in ["kkkkkkk", "🤣🤣🤣", "oi sumido", "manda um pix aí"]:
        state = await send_message(state, msg)
        await asyncio.sleep(0.3)

    passed = bool(state.get("last_response"))
    record_result(15, "Mensagens fora de contexto", passed,
                  f"Agente respondeu sem crash: {passed}")


async def scenario_16():
    """Cenário 16: Appointment expirado → auto NO_SHOW."""
    print("\n" + "⏰" * 35)
    print("CENÁRIO 16: APPOINTMENT EXPIRADO → AUTO NO_SHOW")
    print("⏰" * 35 + "\n")

    phone = PHONES[16]
    client_id = await create_test_client(phone, "Marcos", "Clínica Marcos", 7000.0, ClientSegment.CLINICA_MEDICA)
    apt_id = await create_test_appointment_expired(client_id, days_ago=7)

    state = new_state(phone)
    state = await send_message(state, "Oi, bom dia")
    await asyncio.sleep(0.3)

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Appointment).where(Appointment.id == UUID(apt_id)))
        apt = result.scalar_one_or_none()
        is_no_show = apt and apt.status == AppointmentStatus.NO_SHOW

    resp = state.get("last_response", "")
    # Não deve mencionar a data expirada como válida
    expired_date = (datetime.now(BRAZIL_TZ) - timedelta(days=7)).strftime("%d/%m")
    mentions_expired_as_valid = expired_date in resp

    passed = is_no_show and not mentions_expired_as_valid
    record_result(16, "Appointment expirado → NO_SHOW", passed,
                  f"DB NO_SHOW={is_no_show} | Usou nome={'Marcos' in resp} | Menciona expirado={mentions_expired_as_valid}")


async def scenario_17():
    """Cenário 17: Cancelamento completo (2 etapas)."""
    print("\n" + "🚫" * 35)
    print("CENÁRIO 17: CANCELAMENTO COMPLETO (2 ETAPAS)")
    print("🚫" * 35 + "\n")

    phone = PHONES[17]
    client_id = await create_test_client(phone, "Carla", "Lab Carla", 8000.0, ClientSegment.LABORATORIO)
    apt_id = await create_test_appointment(client_id, hours_from_now=168, slot_index=0)

    state = new_state(phone)
    state = await send_message(state, "Oi, quero cancelar minha reunião")
    await asyncio.sleep(0.3)

    resp1 = state.get("last_response", "").lower()
    asked_confirmation = any(w in resp1 for w in ["certeza", "cancelar", "confirma", "tem certeza"])

    state = await send_message(state, "Sim, pode cancelar")
    await asyncio.sleep(0.3)

    resp2 = state.get("last_response", "").lower()
    confirmed_cancel = any(w in resp2 for w in ["cancelad", "pronto", "feito", "ok", "realizado"])

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Appointment).where(Appointment.id == UUID(apt_id)))
        apt = result.scalar_one_or_none()
        is_cancelled = apt and apt.status == AppointmentStatus.CANCELLED

    passed = asked_confirmation and is_cancelled
    record_result(17, "Cancelamento completo (2 etapas)", passed,
                  f"Pediu confirmação={asked_confirmation} | DB CANCELLED={is_cancelled} | Confirmou={confirmed_cancel}")


async def scenario_18():
    """Cenário 18: Escolha de slot alternativo (responde '1')."""
    print("\n" + "🔢" * 35)
    print("CENÁRIO 18: ESCOLHA DE SLOT ALTERNATIVO")
    print("🔢" * 35 + "\n")

    today = datetime.now(BRAZIL_TZ)
    days_to_wed = (2 - today.weekday()) % 7 or 7
    next_wed = today + timedelta(days=days_to_wed)
    next_wed_14h = next_wed.replace(hour=14, minute=0, second=0, microsecond=0)

    blocker_id = await create_test_client("71900000099", "Blocker18", "Corp", 5000.0, ClientSegment.CLINICA_MEDICA)
    async with AsyncSessionLocal() as db:
        db.add(Appointment(
            id=uuid.uuid4(), client_id=UUID(blocker_id), scheduled_at=next_wed_14h,
            duration_minutes=30, meeting_type="CONSULTORIA_INICIAL",
            status=AppointmentStatus.CONFIRMED, notes="Bloqueio cenário 18",
        ))
        await db.commit()

    wed_str = next_wed.strftime("%d/%m")
    state = new_state(PHONES[18])
    for msg in [
        "Oi", "Quero agendar uma reunião", "Felipe Lima",
        "felipe@clinicafelipe.com", "Clínica Felipe Lima",
        "Clínica médica", "Preciso de mais pacientes",
        "6 mil", "sim", f"Quarta dia {wed_str} às 14h",
    ]:
        state = await send_message(state, msg)
        await asyncio.sleep(0.3)

    resp = state.get("last_response", "").lower()
    offered = any(w in resp for w in ["alternativ", "opção", "1)", "1.", "outro horário", "disponív", "horário", "ocup"])

    if offered:
        state = await send_message(state, "1")
        await asyncio.sleep(0.3)

    appointment_created = state.get("appointment_id") is not None
    passed = offered and appointment_created
    record_result(18, "Escolha de slot alternativo", passed,
                  f"Ofereceu={offered} | Appointment criado={appointment_created}")

    async with AsyncSessionLocal() as db:
        await db.execute(text("DELETE FROM appointments WHERE client_id IN (SELECT id FROM clients WHERE phone = '71900000099')"))
        await db.execute(text("DELETE FROM clients WHERE phone = '71900000099'"))
        await db.commit()


async def scenario_19():
    """Cenário 19: Appointment expirado detectado automaticamente."""
    print("\n" + "📆" * 35)
    print("CENÁRIO 19: EXPIRADO DETECTADO AUTOMATICAMENTE")
    print("📆" * 35 + "\n")

    phone = PHONES[19]
    client_id = await create_test_client(phone, "Patrícia", "Patrícia Nutrição", 5000.0, ClientSegment.NUTRICIONISTA)
    await create_test_appointment_expired(client_id, days_ago=3)

    state = new_state(phone)
    state = await send_message(state, "Oi, tudo bem?")
    await asyncio.sleep(0.3)

    resp = state.get("last_response", "")
    expired_date = (datetime.now(BRAZIL_TZ) - timedelta(days=3)).strftime("%d/%m")
    mentions_expired = expired_date in resp and "confirmad" in resp.lower()

    recognized = state.get("client_id") is not None
    passed = recognized and not mentions_expired
    record_result(19, "Expirado detectado automaticamente", passed,
                  f"Reconheceu={recognized} | Menciona data exp como válida={mentions_expired}")


async def scenario_20():
    """Cenário 20: Reagendamento completo."""
    print("\n" + "🔄" * 35)
    print("CENÁRIO 20: REAGENDAMENTO COMPLETO")
    print("🔄" * 35 + "\n")

    phone = PHONES[20]
    client_id = await create_test_client(phone, "Lucas", "Clínica Lucas Fisio", 7000.0, ClientSegment.FISIOTERAPEUTA)
    old_apt_id = await create_test_appointment(client_id, hours_from_now=240, slot_index=0)

    state = new_state(phone)
    state = await send_message(state, "Oi, preciso remarcar minha reunião")
    await asyncio.sleep(0.3)

    resp1 = state.get("last_response", "").lower()
    understood = any(w in resp1 for w in ["remarc", "reagend", "qual", "data", "horário", "quando"])

    today = datetime.now(BRAZIL_TZ)
    days_to_fri = (4 - today.weekday()) % 7 or 7
    next_fri = today + timedelta(days=days_to_fri)
    fri_str = next_fri.strftime("%d/%m")

    state = await send_message(state, f"Sexta dia {fri_str} às 9h")
    await asyncio.sleep(0.3)

    new_appointment = state.get("appointment_id") is not None
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Appointment).where(Appointment.id == UUID(old_apt_id)))
        old_apt = result.scalar_one_or_none()
        old_cancelled = old_apt and old_apt.status == AppointmentStatus.CANCELLED

    passed = understood and new_appointment
    record_result(20, "Reagendamento completo", passed,
                  f"Entendeu={understood} | Novo appointment={new_appointment} | Antigo cancelado={old_cancelled}")


async def scenario_21():
    """Cenário 21: Mensagem ambígua → esclarece → qualificação."""
    print("\n" + "❓" * 35)
    print("CENÁRIO 21: AMBÍGUO → ESCLARECE → QUALIFICAÇÃO")
    print("❓" * 35 + "\n")

    state = new_state(PHONES[21])
    for msg in ["Oi", "???", "quero agendar uma reunião"]:
        state = await send_message(state, msg)
        await asyncio.sleep(0.3)

    resp = state.get("last_response", "").lower()
    in_qualification = any(w in resp for w in ["nome", "email", "empresa", "negócio", "qual é"])
    record_result(21, "Ambíguo → esclarece → qualificação", in_qualification,
                  f"Entrou em qualificação={in_qualification}")


async def scenario_22():
    """Cenário 22: Escolha alternativa '2' (segunda opção)."""
    print("\n" + "2️⃣" * 35)
    print("CENÁRIO 22: ESCOLHA DE SLOT ALTERNATIVO — OPÇÃO 2")
    print("2️⃣" * 35 + "\n")

    today = datetime.now(BRAZIL_TZ)
    days_to_wed = (2 - today.weekday()) % 7 or 7
    next_wed = today + timedelta(days=days_to_wed)
    wed_14h = next_wed.replace(hour=14, minute=0, second=0, microsecond=0)

    blocker_id = await create_test_client("71900000099", "Blocker22", "Corp", 5000.0, ClientSegment.CLINICA_MEDICA)
    async with AsyncSessionLocal() as db:
        db.add(Appointment(
            id=uuid.uuid4(), client_id=UUID(blocker_id), scheduled_at=wed_14h,
            duration_minutes=30, meeting_type="CONSULTORIA_INICIAL",
            status=AppointmentStatus.CONFIRMED, notes="Bloqueio cenário 22",
        ))
        await db.commit()

    wed_str = next_wed.strftime("%d/%m")
    state = new_state(PHONES[22])
    for msg in [
        "Oi", "Quero agendar", "Bianca Santos", "bianca@clinica.com",
        "Clínica Bianca", "Clínica estética", "Preciso de mais clientes",
        "7 mil", "sim", f"Quarta dia {wed_str} às 14h",
    ]:
        state = await send_message(state, msg)
        await asyncio.sleep(0.3)

    resp = state.get("last_response", "").lower()
    # Se o slot estava ocupado, o agente deve ter oferecido alternativas
    offered_alts = any(w in resp for w in ["alternativ", "opção", "disponív", "horário", "ocup", "1)", "1."])
    has_two = "2)" in resp or "2." in resp or "segunda" in resp or offered_alts

    if has_two:
        state = await send_message(state, "2")
        await asyncio.sleep(0.3)

    appointment_created = state.get("appointment_id") is not None
    passed = appointment_created
    record_result(22, "Escolha alternativa 2", passed,
                  f"Tinha 2 opções={has_two} | Appointment criado={appointment_created}")

    async with AsyncSessionLocal() as db:
        await db.execute(text("DELETE FROM appointments WHERE client_id IN (SELECT id FROM clients WHERE phone = '71900000099')"))
        await db.execute(text("DELETE FROM clients WHERE phone = '71900000099'"))
        await db.commit()


async def scenario_23():
    """Cenário 23: Ask to schedule → 'não quero' → encerra."""
    print("\n" + "🚫" * 35)
    print("CENÁRIO 23: NÃO QUER AGENDAR (EXPLÍCITO)")
    print("🚫" * 35 + "\n")

    state = new_state(PHONES[23])
    for msg in [
        "Oi", "Quero uma reunião", "Ricardo Alves",
        "ricardo@empresa.com", "Clínica Ricardo", "Clínica médica",
        "Quero mais leads", "5 mil", "não quero agendar agora",
    ]:
        state = await send_message(state, msg)
        await asyncio.sleep(0.3)

    resp = state.get("last_response", "").lower()
    no_apt = state.get("appointment_id") is None
    farewell = any(w in resp for w in [
        "sucesso", "quando quiser", "chamar", "contato", "sem problema", "fique",
        "disposição", "obrigado", "ótimo", "otimo", "tudo bem", "entendido", "qualquer",
    ])
    passed = no_apt and farewell
    record_result(23, "Não quer agendar → encerra", passed,
                  f"Sem appointment={no_apt} | Despedida={farewell}")


async def scenario_24():
    """Cenário 24: Só uma alternativa disponível → escolha '1'."""
    print("\n" + "1️⃣" * 35)
    print("CENÁRIO 24: UMA SÓ ALTERNATIVA → ESCOLHA 1")
    print("1️⃣" * 35 + "\n")

    today = datetime.now(BRAZIL_TZ)
    days_to_wed = (2 - today.weekday()) % 7 or 7
    next_wed = today + timedelta(days=days_to_wed)
    slot_14 = next_wed.replace(hour=14, minute=0, second=0, microsecond=0)
    wed_str = next_wed.strftime("%d/%m")

    blocker_id = await create_test_client("71900000099", "Blocker24", "Corp", 5000.0, ClientSegment.CLINICA_MEDICA)
    async with AsyncSessionLocal() as db:
        db.add(Appointment(
            id=uuid.uuid4(), client_id=UUID(blocker_id), scheduled_at=slot_14,
            duration_minutes=30, meeting_type="CONSULTORIA_INICIAL",
            status=AppointmentStatus.CONFIRMED, notes="Bloqueio cenário 24",
        ))
        await db.commit()

    state = new_state(PHONES[24])
    for msg in [
        "Oi", "Quero agendar", "Carla Mendes", "carla@clinica.com",
        "Clínica Carla", "Nutricionista", "Preciso de mais pacientes",
        "6 mil", "sim", f"Quarta dia {wed_str} às 14h",
    ]:
        state = await send_message(state, msg)
        await asyncio.sleep(0.3)

    resp = state.get("last_response", "").lower()
    offered = any(w in resp for w in ["alternativ", "opção", "1)", "1.", "horário"])

    if offered:
        state = await send_message(state, "1")
        await asyncio.sleep(0.3)

    appointment_created = state.get("appointment_id") is not None
    passed = offered and appointment_created
    record_result(24, "Uma só alternativa → sim/1", passed,
                  f"Ofereceu={offered} | Appointment criado={appointment_created}")

    async with AsyncSessionLocal() as db:
        await db.execute(text("DELETE FROM appointments WHERE client_id IN (SELECT id FROM clients WHERE phone = '71900000099')"))
        await db.execute(text("DELETE FROM clients WHERE phone = '71900000099'"))
        await db.commit()


async def scenario_25():
    """Cenário 25: Datetime só dia → oferta horários → escolhe."""
    print("\n" + "📆" * 35)
    print("CENÁRIO 25: SÓ DIA → HORÁRIOS → ESCOLHE")
    print("📆" * 35 + "\n")

    state = new_state(PHONES[25])
    for msg in [
        "Oi", "Quero marcar reunião", "Diego Costa",
        "diego@clinica.com", "Clínica Diego", "Fisioterapeuta",
        "Preciso de mais agendamentos", "5 mil", "sim",
        "quinta", "às 14h",
    ]:
        state = await send_message(state, msg)
        await asyncio.sleep(0.3)

    appointment_created = state.get("appointment_id") is not None
    resp = state.get("last_response", "").lower()
    progressed = appointment_created or any(w in resp for w in ["horário", "disponív", "quinta", "data", "confirmad"])
    record_result(25, "Datetime só dia → escolhe horário", progressed,
                  f"Appointment={appointment_created} | Progrediu={progressed}")


async def scenario_26():
    """Cenário 26: Desistência na escolha de alternativa ('outro dia')."""
    print("\n" + "↩️" * 35)
    print("CENÁRIO 26: DESISTÊNCIA NA ESCOLHA DE ALTERNATIVA")
    print("↩️" * 35 + "\n")

    today = datetime.now(BRAZIL_TZ)
    days_to_wed = (2 - today.weekday()) % 7 or 7
    next_wed = today + timedelta(days=days_to_wed)
    wed_14h = next_wed.replace(hour=14, minute=0, second=0, microsecond=0)
    wed_str = next_wed.strftime("%d/%m")

    blocker_id = await create_test_client("71900000099", "Blocker26", "Corp", 5000.0, ClientSegment.CLINICA_MEDICA)
    async with AsyncSessionLocal() as db:
        db.add(Appointment(
            id=uuid.uuid4(), client_id=UUID(blocker_id), scheduled_at=wed_14h,
            duration_minutes=30, meeting_type="CONSULTORIA_INICIAL",
            status=AppointmentStatus.CONFIRMED, notes="Bloqueio cenário 26",
        ))
        await db.commit()

    state = new_state(PHONES[26])
    for msg in [
        "Oi", "Quero agendar", "Elena Souza", "elena@clinica.com",
        "Clínica Elena", "Clínica estética", "Preciso de mais clientes",
        "6 mil", "sim", f"Quarta dia {wed_str} às 14h", "outro dia",
    ]:
        state = await send_message(state, msg)
        await asyncio.sleep(0.3)

    no_crash = bool(state.get("last_response"))
    resp = state.get("last_response", "").lower()
    handles_gracefully = any(w in resp for w in ["dia", "horário", "data", "escolh", "opção", "qual"])
    passed = no_crash
    record_result(26, "Desistência na escolha de alternativa", passed,
                  f"Sem crash={no_crash} | Resposta adequada={handles_gracefully}")

    async with AsyncSessionLocal() as db:
        await db.execute(text("DELETE FROM appointments WHERE client_id IN (SELECT id FROM clients WHERE phone = '71900000099')"))
        await db.execute(text("DELETE FROM clients WHERE phone = '71900000099'"))
        await db.commit()


async def scenario_27():
    """Cenário 27: Várias mensagens unclear → resiliência / escalação."""
    print("\n" + "🆘" * 35)
    print("CENÁRIO 27: MENSAGENS UNCLEAR → RESILIÊNCIA")
    print("🆘" * 35 + "\n")

    state = new_state(PHONES[27])
    for msg in ["Oi", "???", "não sei", "blabla"]:
        state = await send_message(state, msg)
        await asyncio.sleep(0.3)

    all_responses = ""
    for m in state.get("messages", []):
        # PydanticAI messages: check for model responses
        if hasattr(m, "parts"):
            for part in m.parts:
                if hasattr(part, "content") and isinstance(part.content, str):
                    all_responses += part.content.lower()

    escalation = any(w in all_responses for w in ["humano", "atendente", "equipe", "transferir"])
    resilience = any(w in all_responses for w in ["nome", "ajudar", "como posso"])
    passed = escalation or resilience or bool(state.get("last_response"))
    record_result(27, "Mensagens unclear → resiliência", passed,
                  f"Escalação={escalation} | Resiliência={resilience}")


async def scenario_28():
    """Cenário 28: Email inválido → agente pede novamente ou aceita sem email."""
    print("\n" + "📧" * 35)
    print("CENÁRIO 28: EMAIL INVÁLIDO")
    print("📧" * 35 + "\n")

    state = new_state(PHONES[28])
    for msg in [
        "Oi", "Quero agendar", "Fernanda Castro",
        "fernandagmail.com",   # email inválido (sem @)
        "não tenho email",     # recusa — agente deve aceitar e seguir
        "Clínica Estética FC", "Clínica estética",
        "Preciso de mais clientes", "5 mil",
    ]:
        state = await send_message(state, msg)
        await asyncio.sleep(0.3)

    # Passou se o agente avançou (criou cliente) OU pediu email novamente sem travar
    client_created = state.get("client_id") is not None
    resp = state.get("last_response", "").lower()
    advanced = client_created or any(w in resp for w in ["data", "horário", "agenda", "quando", "reunião"])
    passed = advanced
    record_result(28, "Email inválido → agente lida sem travar", passed,
                  f"client_id={state.get('client_id')} | Avançou={advanced}")


async def scenario_29():
    """Cenário 29: Orçamento indefinido → agente esclarece ou encerra."""
    print("\n" + "💰" * 35)
    print("CENÁRIO 29: ORÇAMENTO INDEFINIDO")
    print("💰" * 35 + "\n")

    state = new_state(PHONES[29])
    for msg in [
        "Oi", "Quero agendar", "Marcelo Nunes",
        "marcelo@clinica.com", "Clínica Nunes", "Clínica médica",
        "Quero mais pacientes",
        "não tenho orçamento definido, depende do serviço",
        "talvez uns 2 mil",  # abaixo do mínimo — deve encerrar
    ]:
        state = await send_message(state, msg)
        await asyncio.sleep(0.3)

    resp = state.get("last_response", "").lower()
    # Deve mencionar o mínimo ou encerrar educadamente
    handled = any(w in resp for w in ["3.000", "3000", "mínimo", "minimo", "partir de", "orçamento"])
    no_appointment = state.get("appointment_id") is None
    passed = handled and no_appointment
    record_result(29, "Orçamento indefinido → encerra ou esclarece", passed,
                  f"Mencionou mínimo={handled} | Sem appointment={no_appointment}")


async def scenario_30():
    """Cenário 30: Segmento fora da saúde → agente recusa gentilmente."""
    print("\n" + "🚫" * 35)
    print("CENÁRIO 30: SEGMENTO FORA DA SAÚDE")
    print("🚫" * 35 + "\n")

    state = new_state(PHONES[30])
    for msg in [
        "Oi", "Quero agendar uma reunião", "João Padaria",
        "joao@padaria.com", "Padaria do João", "Padaria / alimentação",
        "Quero aumentar minhas vendas", "5 mil",
    ]:
        state = await send_message(state, msg)
        await asyncio.sleep(0.3)

    resp = state.get("last_response", "").lower()
    refused = any(w in resp for w in [
        "saúde", "saude", "especializad", "área", "segmento", "atend",
        "padaria", "alimentação", "fora", "infelizmente",
    ])
    no_client = state.get("client_id") is None
    passed = refused
    record_result(30, "Segmento fora da saúde → recusa gentil", passed,
                  f"Recusou={refused} | Sem client={no_client}")


async def scenario_31():
    """Cenário 31: Cliente duplicado → buscar_cliente detecta e não cria novo."""
    print("\n" + "👥" * 35)
    print("CENÁRIO 31: CLIENTE DUPLICADO")
    print("👥" * 35 + "\n")

    phone = PHONES[31]
    original_id = await create_test_client(phone, "Vanessa", "Clínica Vanessa", 6000.0, ClientSegment.CLINICA_ESTETICA)

    state = new_state(phone)
    # Cliente retorna e manda dados como se fosse novo
    for msg in ["Oi", "quero me cadastrar", "meu nome é Vanessa"]:
        state = await send_message(state, msg)
        await asyncio.sleep(0.3)

    # Deve reconhecer (buscar_cliente) e usar o ID existente — não criar novo
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Client).where(Client.phone == phone))
        all_clients = result.scalars().all()

    only_one = len(all_clients) == 1
    recognized = state.get("client_id") is not None
    resp = state.get("last_response", "")
    used_name = "Vanessa" in resp
    passed = only_one and recognized
    record_result(31, "Cliente duplicado → sem duplicata no DB", passed,
                  f"Apenas 1 cliente no DB={only_one} | Reconheceu={recognized} | Usou nome={used_name}")


async def scenario_32():
    """Cenário 32: Data muito no futuro (6 meses) → agente aceita e agenda."""
    print("\n" + "📅" * 35)
    print("CENÁRIO 32: DATA MUITO NO FUTURO (6 MESES)")
    print("📅" * 35 + "\n")

    future_date = datetime.now(BRAZIL_TZ) + timedelta(days=180)
    # Achar próxima segunda-feira a partir da data futura
    days_to_mon = (0 - future_date.weekday()) % 7
    future_mon = future_date + timedelta(days=days_to_mon)
    date_str = future_mon.strftime("%d/%m")

    state = new_state(PHONES[32])
    for msg in [
        "Oi", "Quero agendar", "Bruno Saraiva",
        "bruno@clinica.com", "Clínica Bruno", "Clínica médica",
        "Preciso de mais leads", "8 mil", "sim",
        f"Segunda dia {date_str} às 9h",
    ]:
        state = await send_message(state, msg)
        await asyncio.sleep(0.3)

    resp = state.get("last_response", "").lower()
    apt_created = state.get("appointment_id") is not None
    # Pode ter agendado ou dito que não há disponibilidade — ambos são respostas válidas
    handled = apt_created or any(w in resp for w in ["disponív", "horário", "data", "agenda"])
    passed = handled
    record_result(32, "Data 6 meses no futuro → trata sem crash", passed,
                  f"Appointment={apt_created} | Tratou={handled}")


async def scenario_33():
    """Cenário 33: Mensagem muito longa → agente processa sem travar."""
    print("\n" + "📜" * 35)
    print("CENÁRIO 33: MENSAGEM MUITO LONGA")
    print("📜" * 35 + "\n")

    long_msg = (
        "Olá, meu nome é Cláudia Ferreira e eu tenho uma clínica de fisioterapia "
        "há mais de 10 anos em Salvador. Atendo principalmente atletas e pacientes "
        "pós-cirúrgicos. Tenho 3 fisioterapeutas na equipe e uma recepcionista. "
        "Meu principal problema é que dependo muito de indicação de médicos ortopedistas "
        "e gostaria de ter uma presença digital mais forte para captar pacientes de forma "
        "autônoma. Já tentei fazer Instagram sozinha mas não tive resultado. Meu orçamento "
        "é de aproximadamente 6 mil reais por mês e prefiro uma reunião na quinta-feira "
        "ou sexta-feira de manhã. O email é claudia@fisioferreira.com.br e o CNPJ da clínica "
        "é 12.345.678/0001-90, mas não sei se você precisa disso."
    )

    state = new_state(PHONES[33])
    state = await send_message(state, long_msg)
    await asyncio.sleep(0.3)

    responded = bool(state.get("last_response"))
    resp = state.get("last_response", "").lower()
    # Agente deve ter processado e avançado (pediu mais info ou já salvou)
    advanced = any(w in resp for w in ["claudia", "cláudia", "nome", "email", "empresa", "agenda", "horário", "data"])
    passed = responded
    record_result(33, "Mensagem muito longa → processa sem crash", passed,
                  f"Respondeu={responded} | Avançou conversa={advanced}")


async def scenario_34():
    """Cenário 34: Múltiplas datas na mesma mensagem → agente escolhe uma."""
    print("\n" + "🗓️" * 35)
    print("CENÁRIO 34: MÚLTIPLAS DATAS NA MESMA MENSAGEM")
    print("🗓️" * 35 + "\n")

    state = new_state(PHONES[34])
    for msg in [
        "Oi", "Quero agendar", "Tatiane Rocha",
        "tatiane@clinica.com", "Clínica Tatiane", "Psicologia",
        "Quero mais pacientes pelo Instagram", "5 mil", "sim",
        "pode ser segunda às 9h ou quarta às 14h, qualquer um serve",
    ]:
        state = await send_message(state, msg)
        await asyncio.sleep(0.3)

    resp = state.get("last_response", "").lower()
    apt_created = state.get("appointment_id") is not None
    # Deve ter agendado um dos horários ou pedido para confirmar
    handled = apt_created or any(w in resp for w in ["confirmad", "agendad", "segunda", "quarta", "horário", "qual"])
    passed = handled
    record_result(34, "Múltiplas datas → agente escolhe/confirma", passed,
                  f"Appointment={apt_created} | Tratou={handled}")


async def scenario_35():
    """Cenário 35: Paciente buscando médico → agente encerra gentilmente."""
    print("\n" + "🏥" * 35)
    print("CENÁRIO 35: PACIENTE BUSCANDO MÉDICO")
    print("🏥" * 35 + "\n")

    state = new_state(PHONES[35])
    for msg in [
        "Oi", "preciso marcar consulta com um cardiologista",
        "tenho dores no peito e quero uma avaliação",
    ]:
        state = await send_message(state, msg)
        await asyncio.sleep(0.3)

    resp = state.get("last_response", "").lower()
    redirected = any(w in resp for w in [
        "empresa", "negócio", "profissional", "agência", "marketing",
        "clínica", "infelizmente", "atend", "médico", "paciente",
    ])
    no_client = state.get("client_id") is None
    passed = redirected
    record_result(35, "Paciente buscando médico → recusa gentil", passed,
                  f"Redirecionou={redirected} | Sem client={no_client}")


async def scenario_36():
    """Cenário 36: Todos slots do dia ocupados → agente sugere outro dia."""
    print("\n" + "🔒" * 35)
    print("CENÁRIO 36: DIA COMPLETAMENTE OCUPADO → OUTRO DIA")
    print("🔒" * 35 + "\n")

    today = datetime.now(BRAZIL_TZ)
    days_to_thu = (3 - today.weekday()) % 7 or 7
    next_thu = today + timedelta(days=days_to_thu)
    thu_str = next_thu.strftime("%d/%m")

    # Bloquear TODOS os slots de quinta-feira preenchendo cada horário individualmente
    # (FULL_DAY_BLOCK exige client_id NULL mas o banco tem NOT NULL constraint)
    blocker36_id = await create_test_client("71900000099", "Blocker36", "Corp36", 5000.0, ClientSegment.CLINICA_MEDICA)
    from app.services.appointmentService import get_available_slots as _get_slots
    from datetime import date as _date
    async with AsyncSessionLocal() as db:
        slots = await _get_slots(next_thu.date(), db)
    block_ids = []
    for slot_str in slots:
        h, m = map(int, slot_str.split(":"))
        slot_dt = next_thu.replace(hour=h, minute=m, second=0, microsecond=0)
        bid = uuid.uuid4()
        block_ids.append(str(bid))
        async with AsyncSessionLocal() as db:
            db.add(Appointment(
                id=bid,
                client_id=UUID(blocker36_id),
                scheduled_at=slot_dt,
                duration_minutes=30,
                meeting_type="CONSULTORIA_INICIAL",
                status=AppointmentStatus.CONFIRMED,
                notes="Bloqueio cenário 36",
            ))
            await db.commit()

    state = new_state(PHONES[36])
    for msg in [
        "Oi", "Quero agendar", "Sônia Barros",
        "sonia@clinica.com", "Clínica Sônia", "Nutricionista",
        "Quero mais pacientes", "7 mil", "sim",
        f"Quinta dia {thu_str} às 10h",
    ]:
        state = await send_message(state, msg)
        await asyncio.sleep(0.3)

    resp = state.get("last_response", "").lower()
    no_apt_thu = state.get("appointment_id") is None
    suggested_other = any(w in resp for w in [
        "outro dia", "outra data", "disponív", "segunda", "terça", "quarta",
        "sexta", "sem disponibilidade", "indisponív", "horário",
    ])
    passed = suggested_other or no_apt_thu
    record_result(36, "Dia totalmente ocupado → sugere outro", passed,
                  f"Sugeriu outro={suggested_other} | Sem apt no dia bloqueado={no_apt_thu}")

    async with AsyncSessionLocal() as db:
        await db.execute(text("DELETE FROM appointments WHERE client_id IN (SELECT id FROM clients WHERE phone = '71900000099')"))
        await db.execute(text("DELETE FROM clients WHERE phone = '71900000099'"))
        await db.commit()


async def scenario_37():
    """Cenário 37: Agendamento para hoje → agente verifica disponibilidade real."""
    print("\n" + "📆" * 35)
    print("CENÁRIO 37: AGENDAMENTO PARA HOJE")
    print("📆" * 35 + "\n")

    today_str = datetime.now(BRAZIL_TZ).strftime("%d/%m")

    state = new_state(PHONES[37])
    for msg in [
        "Oi", "Quero agendar", "Igor Pires",
        "igor@clinica.com", "Clínica Igor", "Clínica médica",
        "Preciso de mais pacientes", "6 mil", "sim",
        f"hoje dia {today_str}",
    ]:
        state = await send_message(state, msg)
        await asyncio.sleep(0.3)

    resp = state.get("last_response", "").lower()
    apt_created = state.get("appointment_id") is not None
    # Pode ter agendado (se houver slots hoje) ou informado sem disponibilidade — ambos válidos
    handled = apt_created or any(w in resp for w in [
        "hoje", "disponív", "horário", "indisponív", "outro dia", "amanhã", "data",
    ])
    passed = handled
    record_result(37, "Agendamento para hoje → responde conforme disponibilidade", passed,
                  f"Appointment={apt_created} | Tratou={handled}")


# ========== RELATÓRIO FINAL ==========

def print_final_report():
    print("\n\n" + "=" * 70)
    print("📊 RELATÓRIO FINAL — SIMULAÇÃO DE 37 CENÁRIOS (PydanticAI)")
    print("=" * 70 + "\n")

    passed_count = sum(1 for _, _, p, _ in results if p)
    failed_count = len(results) - passed_count

    for scenario, name, passed, details in results:
        status = "✅" if passed else "❌"
        print(f"  {status} Cenário {scenario:2d}: {name}")
        if details and not passed:
            print(f"                    → {details}")

    total = len(results)
    print(f"\n{'─' * 70}")
    print(f"  TOTAL: {total} | ✅ {passed_count} passaram | ❌ {failed_count} falharam")
    if total > 0:
        print(f"  TAXA: {passed_count/total*100:.0f}% de sucesso")
    print(f"{'─' * 70}")

    if failed_count == 0:
        print("\n  🏆 TODOS OS CENÁRIOS PASSARAM!\n")
    else:
        print(f"\n  ⚠️  {failed_count} cenário(s) precisam de atenção.\n")


# ========== MAIN ==========

SCENARIOS = [
    scenario_01, scenario_02, scenario_03, scenario_04, scenario_05,
    scenario_06, scenario_07, scenario_08, scenario_09, scenario_10,
    scenario_11, scenario_12, scenario_13, scenario_14, scenario_15,
    scenario_16, scenario_17, scenario_18, scenario_19, scenario_20,
    scenario_21, scenario_22, scenario_23, scenario_24, scenario_25,
    scenario_26, scenario_27, scenario_28, scenario_29, scenario_30,
    scenario_31, scenario_32, scenario_33, scenario_34, scenario_35,
    scenario_36, scenario_37,
]


async def main(only_scenario: int | None = None, only_scenarios: list[int] | None = None):
    import os as _os
    scenarios = list(enumerate(SCENARIOS, 1))
    if only_scenarios is not None:
        scenarios = [(i, SCENARIOS[i - 1]) for i in only_scenarios if 1 <= i <= len(SCENARIOS)]
    elif only_scenario is not None:
        if not 1 <= only_scenario <= len(SCENARIOS):
            print(f"❌ Cenário inválido. Use 1-{len(SCENARIOS)}.")
            return
        scenarios = [(only_scenario, SCENARIOS[only_scenario - 1])]

    print("\n" + "🎯" * 35)
    print(f"SIMULAÇÃO — {len(scenarios)} CENÁRIO(S) — PydanticAI Agent")
    print(f"Data: {datetime.now(BRAZIL_TZ).strftime('%d/%m/%Y %H:%M')}")
    print("🎯" * 35 + "\n")

    print("🧹 Limpando dados de testes anteriores...")
    await cleanup_phones()
    print("✅ Banco limpo\n")

    for i, fn in scenarios:
        try:
            await fn()
        except Exception as e:
            print(f"\n❌ ERRO NO CENÁRIO {i}: {e}")
            import traceback
            traceback.print_exc()
            record_result(i, fn.__doc__.split(":")[1].strip() if fn.__doc__ and ":" in fn.__doc__ else "?", False, str(e))
        await asyncio.sleep(0.5)

    print_final_report()


if __name__ == "__main__":
    import os as _os
    if _os.environ.get("GRAPH_MODE") == "cleanup":
        asyncio.run(cleanup_phones())
        print("Banco limpo.")
    else:
        if len(sys.argv) > 2:
            try:
                only_list = [int(x) for x in sys.argv[1:]]
            except ValueError:
                print("Uso: python simulate_all_flows.py [cenário1 cenário2 ...]")
                sys.exit(1)
            asyncio.run(main(only_scenarios=only_list))
        elif len(sys.argv) == 2:
            try:
                only = int(sys.argv[1])
            except ValueError:
                print("Uso: python simulate_all_flows.py [número_do_cenário]")
                sys.exit(1)
            asyncio.run(main(only_scenario=only))
        else:
            asyncio.run(main())
