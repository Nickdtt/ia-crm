"""
StateGraph com dispatcher — cada invocação executa UM nó e para (END).

ARQUITETURA:
- Entry point: dispatcher (olha current_step → roteia para o nó correto)
- Cada nó executa, seta current_step, e vai para END
- Exceções: slot_checker e appointment_creator encadeiam automaticamente
  (não precisam de input do usuário)

FLUXO DE current_step:
  (vazio/greeting) → greeting → END             [aguarda input]
  question_answerer → question_answerer → END    [aguarda input]  
  lead_collector    → simple_lead_collector → END [aguarda input]
  ask_to_schedule   → ask_to_schedule → END      [aguarda input]
  datetime_collector→ datetime_collector → END    [aguarda input]
                      OU → slot_checker → appointment_creator → confirmation → END
  confirmation      → END (conversa finalizada)
"""

from langgraph.graph import StateGraph, END
from app.agent.state import MarketingCRMState
from app.agent.nodes.greeting import greeting_node
from app.agent.nodes.question_answerer import question_answerer_node
from app.agent.nodes.simple_lead_collector import simple_lead_collector_node
from app.agent.nodes.ask_to_schedule import ask_to_schedule_node
from app.agent.nodes.datetime_collector import datetime_collector_node
from app.agent.nodes.slot_checker import slot_checker_node
from app.agent.nodes.appointment_creator import appointment_creator_node
from app.agent.nodes.confirmation import confirmation_node


# ========== DISPATCHER ==========

async def dispatcher_node(state: MarketingCRMState) -> dict:
    """
    Nó de entrada — não faz nada, só existe para o roteamento condicional.
    O roteamento real acontece em route_dispatcher.
    """
    return {}


def route_dispatcher(state: MarketingCRMState) -> str:
    """
    Roteia para o nó correto baseado no current_step persistido.
    
    Lógica:
    - Sem current_step ou "greeting" → greeting (primeira mensagem)
    - "question_answerer" → question_answerer (respondeu, espera próxima pergunta ou lead)
    - "lead_collector" → simple_lead_collector (coletando campos)
    - "ask_to_schedule" → ask_to_schedule (ofereceu/espera resposta)
    - "datetime_collector" → datetime_collector (coletando data/hora)
    - "confirmation" → confirmation (já encerrou, mas recebeu msg nova)
    """
    step = state.get("current_step", "")
    mode = state.get("conversation_mode", "")
    
    # Conversa já completada → reseta (chatControllers já trata isso, mas por segurança)
    if mode == "completed":
        print("🔄 Dispatcher: conversa completada, reenviando para greeting")
        return "greeting"
    
    # PRIMEIRA MENSAGEM — sem step definido
    if not step or step == "greeting":
        # Se já fez greeting (presentation_done), avança
        if state.get("presentation_done"):
            # Decidir próximo passo baseado no estado
            if state.get("lead_collection_complete"):
                if state.get("asked_to_schedule") and state.get("wants_to_schedule") is None:
                    return "ask_to_schedule"
                if state.get("wants_to_schedule") is True:
                    return "datetime_collector"
                if state.get("wants_to_schedule") is False:
                    return "confirmation"
                return "ask_to_schedule"
            return "question_answerer"
        return "greeting"
    
    # QUESTION ANSWERER — respondeu pergunta
    if step == "question_answerer":
        if state.get("lead_collection_complete"):
            return "ask_to_schedule"
        # Só avança para lead_collector se o usuário ACEITOU responder perguntas
        if state.get("permission_granted") is True:
            return "simple_lead_collector"
        # Caso contrário, continua respondendo perguntas (permission pendente/recusada)
        return "question_answerer"
    
    # LEAD COLLECTOR — continua coletando ou avança
    if step == "lead_collector":
        if state.get("lead_collection_complete"):
            return "ask_to_schedule"
        return "simple_lead_collector"
    
    # ASK TO SCHEDULE — analisa resposta do usuário
    if step == "ask_to_schedule":
        # Se já perguntou e espera resposta, reprocessa
        if state.get("asked_to_schedule"):
            return "ask_to_schedule"
        return "ask_to_schedule"
    
    # DATETIME COLLECTOR — coletando data/hora
    if step == "datetime_collector":
        return "datetime_collector"
    
    # SLOT CHECKER — não deveria chegar aqui (encadeia automaticamente)
    if step == "slot_checker":
        return "datetime_collector"
    
    # APPOINTMENT CREATOR — não deveria chegar aqui
    if step == "appointment_creator":
        return "confirmation"
    
    # CONFIRMATION — conversa encerrada
    if step == "confirmation":
        return "greeting"
    
    # Fallback
    print(f"⚠️ Dispatcher: step desconhecido '{step}', voltando para greeting")
    return "greeting"


# ========== ROTEAMENTO PÓS-NÓ ==========

def route_after_lead_collector(state: MarketingCRMState) -> str:
    """Após lead_collector: se completo, encadeia para ask_to_schedule. Senão, END."""
    if state.get("lead_collection_complete"):
        # Coleta completa → encadeia automaticamente para ask_to_schedule
        return "ask_to_schedule"
    # Ainda coletando → END (aguarda próximo campo)
    return "__end__"


def route_after_ask(state: MarketingCRMState) -> str:
    """Após ask_to_schedule: se já tem resposta, encadeia. Senão, END."""
    wants = state.get("wants_to_schedule")
    if wants is True:
        # Usuário aceitou → encadeia para datetime_collector
        return "datetime_collector"
    if wants is False:
        # Usuário recusou → encadeia para confirmation
        return "confirmation"
    # Ainda não tem resposta (acabou de perguntar) → END
    return "__end__"


def route_after_datetime(state: MarketingCRMState) -> str:
    """Após datetime_collector: se extraiu data, encadeia para slot_checker."""
    if state.get("requested_datetime"):
        return "slot_checker"
    # Não conseguiu extrair → END (pede novamente na próxima msg)
    return "__end__"


def route_after_slot_check(state: MarketingCRMState) -> str:
    """Após slot_checker: se disponível, encadeia para appointment_creator."""
    if state.get("slot_available") or state.get("chosen_slot"):
        return "appointment_creator"
    # Indisponível → END (oferece alternativas, espera nova data)
    return "__end__"


# ========== WRAPPERS PARA SETAR current_step ==========

async def greeting_wrapper(state: MarketingCRMState) -> dict:
    result = await greeting_node(state)
    result["current_step"] = "greeting"
    return result


async def question_answerer_wrapper(state: MarketingCRMState) -> dict:
    result = await question_answerer_node(state)
    result["current_step"] = "question_answerer"
    return result


async def lead_collector_wrapper(state: MarketingCRMState) -> dict:
    result = await simple_lead_collector_node(state)
    result["current_step"] = "lead_collector"
    return result


async def ask_to_schedule_wrapper(state: MarketingCRMState) -> dict:
    result = await ask_to_schedule_node(state)
    result["current_step"] = "ask_to_schedule"
    return result


async def datetime_collector_wrapper(state: MarketingCRMState) -> dict:
    result = await datetime_collector_node(state)
    result["current_step"] = "datetime_collector"
    return result


async def slot_checker_wrapper(state: MarketingCRMState) -> dict:
    result = await slot_checker_node(state)
    result["current_step"] = "slot_checker"
    return result


async def appointment_creator_wrapper(state: MarketingCRMState) -> dict:
    result = await appointment_creator_node(state)
    result["current_step"] = "appointment_creator"
    return result


async def confirmation_wrapper(state: MarketingCRMState) -> dict:
    result = await confirmation_node(state)
    result["current_step"] = "confirmation"
    result["conversation_mode"] = "completed"
    return result


# ========== GRAPH FACTORY ==========

def create_marketing_crm_graph() -> StateGraph:
    """Cria e compila o StateGraph com dispatcher."""
    
    workflow = StateGraph(MarketingCRMState)
    
    # === NÓS ===
    workflow.add_node("dispatcher", dispatcher_node)
    workflow.add_node("greeting", greeting_wrapper)
    workflow.add_node("question_answerer", question_answerer_wrapper)
    workflow.add_node("simple_lead_collector", lead_collector_wrapper)
    workflow.add_node("ask_to_schedule", ask_to_schedule_wrapper)
    workflow.add_node("datetime_collector", datetime_collector_wrapper)
    workflow.add_node("slot_checker", slot_checker_wrapper)
    workflow.add_node("appointment_creator", appointment_creator_wrapper)
    workflow.add_node("confirmation", confirmation_wrapper)
    
    # === ENTRY POINT ===
    workflow.set_entry_point("dispatcher")
    
    # === EDGES ===
    
    # DISPATCHER → nó correto baseado em current_step
    workflow.add_conditional_edges(
        "dispatcher",
        route_dispatcher,
        {
            "greeting": "greeting",
            "question_answerer": "question_answerer",
            "simple_lead_collector": "simple_lead_collector",
            "ask_to_schedule": "ask_to_schedule",
            "datetime_collector": "datetime_collector",
            "confirmation": "confirmation",
        }
    )
    
    # GREETING → END (aguarda próxima mensagem)
    workflow.add_edge("greeting", END)
    
    # QUESTION_ANSWERER → END (respondeu, aguarda)
    workflow.add_edge("question_answerer", END)
    
    # LEAD_COLLECTOR → END ou encadeia para ask_to_schedule (se completo)
    workflow.add_conditional_edges(
        "simple_lead_collector",
        route_after_lead_collector,
        {
            "ask_to_schedule": "ask_to_schedule",
            "__end__": END,
        }
    )
    
    # ASK_TO_SCHEDULE → END ou encadeia (se já tem resposta do usuário)
    workflow.add_conditional_edges(
        "ask_to_schedule",
        route_after_ask,
        {
            "datetime_collector": "datetime_collector",
            "confirmation": "confirmation",
            "__end__": END,
        }
    )
    
    # DATETIME_COLLECTOR → END ou encadeia para slot_checker
    workflow.add_conditional_edges(
        "datetime_collector",
        route_after_datetime,
        {
            "slot_checker": "slot_checker",
            "__end__": END,
        }
    )
    
    # SLOT_CHECKER → appointment_creator ou END (alternativas)
    workflow.add_conditional_edges(
        "slot_checker",
        route_after_slot_check,
        {
            "appointment_creator": "appointment_creator",
            "__end__": END,
        }
    )
    
    # APPOINTMENT_CREATOR → confirmation (sempre encadeia)
    workflow.add_edge("appointment_creator", "confirmation")
    
    # CONFIRMATION → END
    workflow.add_edge("confirmation", END)
    
    # Compilar
    compiled = workflow.compile()
    
    print("=" * 80)
    print("✅ MARKETING CRM GRAPH COMPILADO (DISPATCHER + END POR NÓ)")
    print("=" * 80)
    print("\nARQUITETURA:")
    print("  dispatcher → [nó baseado em current_step] → END")
    print("\nFLUXO:")
    print("  1. greeting → END (apresentação, aguarda input)")
    print("  2. question_answerer → END (RAG, aguarda input)")
    print("  3. simple_lead_collector → END (coleta 1 campo, aguarda)")
    print("  4. ask_to_schedule → END ou → datetime_collector")
    print("  5. datetime_collector → END ou → slot_checker")
    print("  6. slot_checker → appointment_creator (encadeia)")
    print("  7. appointment_creator → confirmation (encadeia)")
    print("  8. confirmation → END (fim)")
    print("=" * 80)
    
    return compiled


# Singleton
marketing_crm_graph = create_marketing_crm_graph()
