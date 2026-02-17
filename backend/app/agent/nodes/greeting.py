from langchain_core.messages import AIMessage
from app.agent.state import MarketingCRMState
from app.core.database import AsyncSessionLocal
from sqlalchemy import select
from app.models.client import Client
from app.models.appointment import Appointment


async def greeting_node(state: MarketingCRMState) -> dict:
    """
    NODE: GREETING - Apresentação inicial do agente.
    
    Verifica se o cliente já existe no banco (por telefone):
    - Se existe com appointments → mode="returning_with_appointment" (NÃO vai para END, encadeia)
    - Se existe sem appointments → mode="returning_without_appointment" (NÃO vai para END, encadeia)
    - Se não existe → apresentação normal → END (aguarda resposta)
    
    Para clientes retornando, NÃO envia saudação aqui.
    Apenas carrega dados e seta o mode. O returning_client_handler
    faz a saudação única + resposta contextualizada.
    
    DETECÇÃO DE CANCELAMENTO:
    - Se appointment_confirmed=True e user_input contém "cancelar", redireciona
    """
    
    # Detectar solicitação de cancelamento
    user_input = state.get("user_input", "").lower()
    appointment_confirmed = state.get("appointment_confirmed", False)
    appointment_id = state.get("appointment_id")
    
    if appointment_confirmed and appointment_id and any(kw in user_input for kw in ["cancelar", "cancela", "desmarcar", "desistir"]):
        print("🚫 Greeting: Detectou solicitação de cancelamento")
        
        # Buscar appointment no banco para cancelar
        async with AsyncSessionLocal() as db:
            from app.services.appointmentService import cancel_appointment
            try:
                await cancel_appointment(appointment_id, "Cancelado pelo cliente via chat", db)
                await db.commit()
                
                cancel_message = """Entendi! Seu agendamento foi cancelado. 😊

Se quiser reagendar ou precisar de qualquer informação, é só me chamar! Estou aqui para ajudar."""
                
                return {
                    "messages": [AIMessage(content=cancel_message)],
                    "appointment_confirmed": False,  # Reset flag
                    "appointment_id": None,
                    "conversation_mode": "idle",
                    "current_step": "greeting"
                }
            except Exception as e:
                print(f"❌ Erro ao cancelar: {e}")
                return {
                    "messages": [AIMessage(content="Desculpe, tive um problema ao processar o cancelamento. Pode tentar novamente?")],
                    "current_step": "greeting"
                }
    
    phone = state.get("phone")
    
    # Verificar se cliente existe no banco
    if phone:
        print(f"🔍 Verificando se cliente {phone} já existe...")
        
        async with AsyncSessionLocal() as db:
            # Buscar cliente por telefone
            result = await db.execute(
                select(Client).where(Client.phone == phone)
            )
            existing_client = result.scalar_one_or_none()
            
            if existing_client:
                print(f"✅ Cliente retornando encontrado: {existing_client.first_name} {existing_client.last_name}")
                
                # Buscar appointments do cliente
                result = await db.execute(
                    select(Appointment).where(Appointment.client_id == existing_client.id)
                )
                appointments = result.scalars().all()
                
                # Montar client_data do banco
                client_data = {
                    "first_name": existing_client.first_name,
                    "last_name": existing_client.last_name,
                    "full_name": f"{existing_client.first_name} {existing_client.last_name}",
                    "phone": existing_client.phone,
                    "email": existing_client.email,
                    "company_name": existing_client.company_name,
                    "segment": existing_client.segment.value if existing_client.segment else None,
                    "monthly_budget": float(existing_client.monthly_budget) if existing_client.monthly_budget else None,
                    "main_marketing_problem": existing_client.main_marketing_problem,
                }
                
                if appointments:
                    active = [a for a in appointments if a.status.value in ("pending", "confirmed")]
                    mode = "returning_with_appointment" if active else "returning_without_appointment"
                    print(f"📅 Cliente tem {len(active)} agendamento(s) ativo(s)")
                else:
                    mode = "returning_without_appointment"
                    print(f"⚠️  Cliente existe mas sem agendamentos")
                
                print(f"🔄 Modo definido: {mode} (encadeia para returning_client_handler)")
                
                # NÃO envia mensagem aqui. NÃO vai para END.
                # O returning_client_handler faz saudação + resposta contextualizada.
                return {
                    "presentation_done": True,
                    "conversation_mode": mode,
                    "client_id": str(existing_client.id),
                    "client_data": client_data,
                    "current_step": "greeting",
                }
    
    # Cliente novo - apresentação padrão
    print("👋 Greeting: Cliente novo - apresentação padrão")
    
    greeting_message = """Oi! Sou o agente virtual da Isso não é uma agência, agência de marketing digital.

Como posso ajudar?"""
    
    return {
        "messages": [AIMessage(content=greeting_message)],
        "presentation_done": True,
        "conversation_mode": "greeting",
        "current_step": "greeting"
    }
