from langchain_core.messages import AIMessage
from datetime import datetime, timedelta
from typing import Literal

from app.core.database import AsyncSessionLocal
from app.agent.state import MarketingCRMState
from app.services.appointmentService import get_available_slots


async def slot_checker_node(state: MarketingCRMState) -> dict:
    """NODE: SLOT_CHECKER - Verifica disponibilidade usando get_available_slots()."""
    
    requested_datetime = state.get("requested_datetime")
    
    if not requested_datetime:
        print("⚠️ Slot Checker: requested_datetime não encontrado")
        return {"current_step": "slot_checker"}
    
    requested_date = requested_datetime.date()
    requested_time = requested_datetime.strftime("%H:%M")
    
    async with AsyncSessionLocal() as db:
        available_slots = await get_available_slots(requested_date, db)
    
    print(f"🔍 Slot Checker: Slots disponíveis em {requested_date}: {available_slots}")
    print(f"🔍 Slot Checker: Cliente solicitou: {requested_time}")
    
    if requested_time in available_slots:
        print("✅ Slot disponível - pode agendar")
        return {
            "slot_available": True,
            "current_step": "slot_checker"
        }
    
    # Slot indisponível — encontrar alternativas próximas
    print("❌ Slot indisponível - buscando alternativas")
    
    # Pegar até 3 slots disponíveis mais próximos do horário desejado
    def time_to_minutes(time_str):
        h, m = map(int, time_str.split(":"))
        return h * 60 + m
    
    requested_minutes = time_to_minutes(requested_time)
    
    # Ordena por proximidade ao horário solicitado
    sorted_slots = sorted(available_slots, key=lambda s: abs(time_to_minutes(s) - requested_minutes))
    alternatives = sorted_slots[:3]
    
    date_str = requested_date.strftime("%d/%m")
    
    if alternatives:
        alt_str = ", ".join([f"{s}h" for s in alternatives])
        message = (
            f"Infelizmente o horário das {requested_time}h não está disponível no dia {date_str}. 😕\n\n"
            f"Horários disponíveis mais próximos: **{alt_str}**\n\n"
            f"Qual você prefere? Ou pode sugerir outra data!"
        )
    else:
        message = (
            f"Não há horários disponíveis no dia {date_str}. 😕\n\n"
            f"Pode sugerir outra data? Atendemos Segunda a Sexta, das 9h às 12h e das 14h às 18h."
        )
    
    print(f"📅 Alternativas oferecidas: {alternatives}")
    
    # Converte date para datetime para salvar no state
    from datetime import datetime
    from zoneinfo import ZoneInfo
    last_requested_datetime = datetime.combine(requested_date, datetime.min.time(), tzinfo=ZoneInfo("America/Sao_Paulo"))
    
    return {
        "slot_available": False,
        "requested_datetime": None,
        "last_requested_date": last_requested_datetime,  # Salva como datetime
        "messages": [AIMessage(content=message)],
        "current_step": "datetime_collector"  # Volta para coletar nova data
    }
