from langchain_core.messages import AIMessage

from app.core.database import AsyncSessionLocal
from app.agent.state import MarketingCRMState
from app.services.appointmentService import create_appointment, cancel_appointment
from app.services.clientService import create_client
from app.schemas.appointmentSchema import AppointmentCreate
from app.schemas.clientSchema import ClientCreate
from app.models.appointment import Appointment, AppointmentStatus
from sqlalchemy import select


async def appointment_creator_node(state: MarketingCRMState) -> dict:
    """NODE: APPOINTMENT_CREATOR - Cria lead (client) + appointment no banco.
    
    PORTFOLIO VERSION: aceita apenas dados mínimos do lead:
    - lead_name (obrigatório)
    - lead_email (obrigatório)
    - lead_interest (obrigatório)
    - phone gerado automaticamente como web-{session_id[:8]}
    - Campos opcionais preenchidos com defaults: segment=OUTRO, budget=1000
    """
    
    # Determinar datetime final
    slot_available = state.get("slot_available")
    
    if slot_available:
        scheduled_at = state.get("requested_datetime")
    else:
        scheduled_at = state.get("chosen_slot")
    
    if not scheduled_at:
        print("⚠️ Appointment Creator: Nenhum horário definido")
        return {"current_step": "appointment_creator"}
    
    # Verifica se já existe client_id (caso reutilizado de fluxo legacy)
    client_id = state.get("client_id")
    
    # Se não tem client_id, cria novo lead no banco
    if not client_id:
        lead_name = state.get("lead_name")
        lead_email = state.get("lead_email")
        lead_interest = state.get("lead_interest")
        session_id = state.get("session_id", "unknown")
        
        if not (lead_name and lead_email and lead_interest):
            print(f"❌ Dados insuficientes: name={lead_name}, email={lead_email}, interest={lead_interest}")
            return {
                "messages": [AIMessage(content="Ops! Ainda preciso do seu nome, email e o que você procura. Pode me passar essas informações?")],
                "current_step": "appointment_creator"
            }
        
        # Gera telefone automático
        phone = f"web-{session_id[:8]}" if len(session_id) >= 8 else f"web-{session_id}"
        
        # Separa nome em first_name + last_name
        name_parts = lead_name.strip().split()
        first_name = name_parts[0]
        last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else name_parts[0]
        
        async with AsyncSessionLocal() as db:
            # Verifica se já existe cliente com esse telefone
            from app.services.clientService import get_client_by_phone
            
            try:
                existing_client = await get_client_by_phone(db, phone)
                if existing_client:
                    client_id = existing_client.id
                    print(f"♻️ Cliente existente reutilizado: {existing_client.full_name} ({existing_client.email}) - ID: {client_id}")
                else:
                    # Cria novo cliente
                    client_data = ClientCreate(
                        first_name=first_name,
                        last_name=last_name,
                        phone=phone,
                        email=lead_email,
                        main_marketing_problem=lead_interest,
                        notes=f"Lead capturado via chat web. Interesse: {lead_interest}"
                    )
                    
                    client = await create_client(client_data, db)
                    client_id = client.id
                    print(f"✅ Lead criado: {client.full_name} ({client.email}) - ID: {client_id}")
                
            except Exception as e:
                print(f"❌ Erro ao criar/buscar lead: {type(e).__name__}: {e}")
                return {
                    "messages": [AIMessage(content="Desculpe, tive um problema ao registrar seus dados. Pode tentar novamente?")],
                    "current_step": "appointment_creator"
                }
    
    # Agora client_id existe (criado ou reutilizado)
    is_reschedule = False
    
    async with AsyncSessionLocal() as db:
        # Verifica se já tem appointment ativo (remarcação)
        stmt = (
            select(Appointment)
            .where(Appointment.client_id == client_id)
            .where(Appointment.status.in_([AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED]))
            .order_by(Appointment.scheduled_at.asc())
        )
        result = await db.execute(stmt)
        active_appointments = result.scalars().all()
        
        if active_appointments:
            is_reschedule = True
            for apt in active_appointments:
                print(f"🔄 Cancelando appointment anterior: {apt.id} ({apt.scheduled_at})")
                await cancel_appointment(
                    appointment_id=apt.id,
                    reason="Remarcado pelo cliente via chat web",
                    db=db
                )
        
        # Criar novo appointment
        appointment_data = AppointmentCreate(
            client_id=client_id,
            scheduled_at=scheduled_at,
            duration_minutes=40,
            meeting_type="Consultoria Gratuita",
            notes="Remarcação via chat web" if is_reschedule else "Agendamento via LangGraph Agent (chat web)"
        )
        
        appointment = await create_appointment(appointment_data, db)
        appointment_id = appointment.id
    
    print(f"✅ Appointment {'remarcado' if is_reschedule else 'criado'}: {appointment_id} para {scheduled_at}")
    
    # Formatar mensagem de confirmação
    scheduled_formatted = scheduled_at.strftime("%d/%m/%Y às %Hh%M" if scheduled_at.minute > 0 else "%d/%m/%Y às %Hh")
    dia_semana = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"][scheduled_at.weekday()]
    
    first_name = state.get("lead_name", "").split()[0] if state.get("lead_name") else ""
    
    if is_reschedule:
        confirmation_message = (
            f"Pronto, {first_name}! Sua reunião foi remarcada com sucesso 🎉\n\n"
            f"📅 {dia_semana}, {scheduled_formatted}\n"
            f"⏱️ Duração: 40 minutos\n"
            f"💻 Google Meet (link enviado por email)\n\n"
            f"Qualquer coisa, é só chamar!"
        )
    else:
        confirmation_message = (
            f"Pronto, {first_name}! 🎉\n\n"
            f"Seu agendamento está confirmado para {scheduled_formatted}!\n\n"
            f"Em breve você receberá o link do Google Meet por email.\n\n"
            f"📅 {dia_semana}, {scheduled_formatted}\n"
            f"⏱️ Duração: 40 minutos\n"
            f"💻 Google Meet\n\n"
            f"Nos vemos em breve!"
        )
    
    return {
        "messages": [AIMessage(content=confirmation_message)],
        "client_id": client_id,
        "appointment_id": appointment_id,
        "appointment_confirmed": True,
        "conversation_mode": "completed",
        "current_step": "appointment_creator"
    }
