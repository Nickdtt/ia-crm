from langchain_core.messages import AIMessage

from app.agent.state import MarketingCRMState


async def confirmation_node(state: MarketingCRMState) -> dict:
    """
    NODE: CONFIRMATION
    
    Função: Mensagem final — após agendamento OU após recusa.
    """
    
    wants_to_schedule = state.get("wants_to_schedule")
    
    # CASO 1: Usuário recusou agendar
    if wants_to_schedule is False:
        lead_name = state.get("lead_name", "")
        first_name = lead_name.split()[0] if lead_name else "Você"
        
        farewell = (
            f"Sem problemas, {first_name}! 😊\n\n"
            f"Quando quiser conversar sobre estratégias de marketing digital, "
            f"é só voltar aqui. Estamos à disposição!\n\n"
            f"Até mais! 👋"
        )
        
        return {
            "messages": [AIMessage(content=farewell)],
            "final_response": farewell,
            "conversation_mode": "idle",  # Volta para idle
            "current_step": "confirmation"
        }
    
    # CASO 2: Agendamento criado com sucesso
    client_data = state.get("client_data", {})
    first_name = client_data.get("first_name", "Cliente")
    
    # Pega data/hora do agendamento (requested_datetime ou chosen_slot)
    final_datetime = state.get("requested_datetime") or state.get("chosen_slot")
    date_str = final_datetime.strftime("%d/%m/%Y às %H:%M") if final_datetime else ""
    
    confirmation_message = f"""Pronto, {first_name}! 🎉

Seu agendamento está confirmado para {date_str}!

Em breve você receberá um email com:
✅ Link da reunião (Google Meet)
✅ Confirmação de data e horário
✅ Contato direto do time

Vamos montar uma estratégia incrível para sua empresa crescer no digital! 

Qualquer dúvida antes da reunião, é só chamar. Até lá! 👋"""
    
    return {
        "messages": [AIMessage(content=confirmation_message)],
        "final_response": confirmation_message,
        "conversation_mode": "idle",  # Volta para idle - aguardando nova interação (ex: cancelamento)
        "appointment_confirmed": True,  # Flag para detectar que já tem agendamento
        "current_step": "confirmation"
    }
