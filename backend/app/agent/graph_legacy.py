from langgraph.graph import StateGraph, END
from app.agent.state import MarketingCRMState
from app.agent.nodes.greeting import greeting_node
from app.agent.nodes.intent_analyzer import intent_analyzer_node, route_after_intent
from app.agent.nodes.question_answerer import question_answerer_node
from app.agent.nodes.qualification_agent import qualification_agent_node, check_qualification_complete
from app.agent.nodes.budget_filter import budget_filter_node, route_after_budget
from app.agent.nodes.ask_to_schedule import ask_to_schedule_node, route_after_ask
from app.agent.nodes.datetime_collector import datetime_collector_node, route_after_datetime
from app.agent.nodes.slot_checker import slot_checker_node, route_after_slot_check
from app.agent.nodes.alternative_slots import alternative_slots_node, route_after_alternative
from app.agent.nodes.appointment_creator import appointment_creator_node
from app.agent.nodes.confirmation import confirmation_node
from app.agent.nodes.fallback import fallback_node, thankyou_node
from app.agent.nodes.returning_client_handler import returning_client_handler_node


# Mapeamento declarativo: conversation_mode → entry point
MODE_ENTRY_MAP = {
    "qualification": "qualification_agent",
    "scheduling": "ask_to_schedule",
    "question": "question_answerer",
    "returning_with_appointment": "returning_client_handler",
    "returning_without_appointment": "returning_client_handler",
    "requalification": "qualification_agent"  # Reusa qualificação com dados parciais
}


def determine_entry_point(state: MarketingCRMState) -> str:
    """
    Determina o entry point dinâmico baseado no estado da conversa.
    
    ESTRATÉGIA HÍBRIDA:
    1. Tenta usar conversation_mode (declarativo) quando disponível
    2. Fallback para lógica baseada em flags (compatibilidade)
    
    Lógica completa (ordem de prioridade):
    
    A. MODO DECLARATIVO (conversation_mode explícito)
       - qualification → qualification_agent
       - scheduling → ask_to_schedule
       - question → question_answerer
       - returning_with_appointment → returning_client_handler
       - returning_without_appointment → returning_client_handler
    
    B. FALLBACKS BASEADOS EM FLAGS (compatibilidade com código legado):
       1. Continuando qualificação (permission_asked mas não completo)
       2. Oferecendo agendamento (qualificado + aprovado budget)
       3. Analisando resposta sobre agendamento
       4. Coletando data/hora
       5. Verificando disponibilidade
       6. Oferecendo horários alternativos
       7. Criando agendamento
       8. Analisando intenção pós-pergunta
       9. Analisando primeira resposta
       10. Primeira interação (greeting)
    """
    
    # A. MODO DECLARATIVO: conversation_mode explícito
    mode = state.get("conversation_mode")
    
    if mode and mode in MODE_ENTRY_MAP:
        target = MODE_ENTRY_MAP[mode]
        print(f"↪️ Mode={mode} → {target}")
        return target
    
    # B. FALLBACKS BASEADOS EM FLAGS (compatibilidade)
    
    # 1. Continuando qualificação
    if state.get("permission_asked") and not state.get("qualification_complete"):
        print("↪️ [Fallback] Continuando coleta de qualificação...")
        return "qualification_agent"
    
    # 2. Qualificado e aprovado no budget, oferece agendamento
    if (state.get("qualification_complete") and 
        state.get("budget_qualified") and 
        not state.get("asked_to_schedule")):
        print("↪️ [Fallback] Oferecendo agendamento...")
        return "ask_to_schedule"
    
    # 3. Já perguntou se quer agendar, aguarda resposta
    if (state.get("asked_to_schedule") and 
        state.get("wants_to_schedule") is None):
        print("↪️ [Fallback] Analisando resposta sobre agendamento...")
        return "ask_to_schedule"
    
    # 4. Cliente aceitou agendar, coleta data/hora
    if (state.get("wants_to_schedule") is True and 
        state.get("requested_datetime") is None and
        state.get("chosen_slot") is None):
        print("↪️ [Fallback] Coletando data/hora específica...")
        return "datetime_collector"
    
    # 5. Data/hora coletada, verifica disponibilidade
    if (state.get("requested_datetime") is not None and 
        state.get("slot_available") is None):
        print("↪️ [Fallback] Verificando disponibilidade...")
        return "slot_checker"
    
    # 6. Slot não disponível, oferece alternativas
    if (state.get("slot_available") is False and 
        state.get("alternative_slots") and
        state.get("chosen_slot") is None):
        print("↪️ [Fallback] Oferecendo horários alternativos...")
        return "alternative_slots"
    
    # 7. Pronto para criar agendamento (slot disponível OU escolheu alternativa)
    if ((state.get("slot_available") is True and state.get("requested_datetime")) or
        (state.get("chosen_slot") is not None)):
        print("↪️ [Fallback] Criando agendamento...")
        return "appointment_creator"
    
    # 8. Respondeu pergunta, analisa intenção da resposta
    if (state.get("initial_intent") == "has_question" and 
        state.get("permission_asked") and
        not state.get("initial_intent_captured")):
        print("↪️ [Fallback] Analisando intenção pós-resposta...")
        return "intent_analyzer"
    
    # 9. Apresentação feita mas ainda não capturou intenção inicial
    if state.get("presentation_done") and not state.get("initial_intent_captured"):
        print("↪️ [Fallback] Analisando intenção da primeira resposta...")
        return "intent_analyzer"
    
    # 10. Primeira interação - apresentação
    if not state.get("presentation_done"):
        print("↪️ [Fallback] Iniciando conversa (apresentação)...")
        return "greeting"
    
    # 11. Default: volta para intent_analyzer
    print("↪️ [Default] Estado não mapeado, analisando intenção...")
    return "intent_analyzer"


def create_marketing_crm_graph():
    """
    Cria o grafo multiagente para agendamento de reuniões de marketing.
    
    FLUXO COMPLETO REFATORADO:
    
    Entry Point Dinâmico → determine_entry_point()
    
    1. GREETING: 
       - Apresentação: "Oi! Sou o agente virtual da Isso não é uma agência. Como posso ajudar?"
       - Sempre → END (aguarda primeira resposta)
    
    2. INTENT_ANALYZER:
       - Classifica primeira resposta em wants_meeting/has_question/unknown
       - wants_meeting → QUALIFICATION_AGENT
       - has_question → QUESTION_ANSWERER
       - unknown → GREETING (pede clarificação)
    
    3. QUESTION_ANSWERER:
       - Responde pergunta do cliente
       - Pede permissão para qualificar na mesma mensagem
       - Sempre → END (aguarda resposta sobre permissão)
       - [Próxima interação: INTENT_ANALYZER analisa se aceitou qualificação]
    
    4. QUALIFICATION_AGENT:
       - Coleta 6 campos progressivamente (one-by-one)
       - Cria Client no banco quando completo
       - continue → QUALIFICATION_AGENT (loop, coleta próximo campo)
       - complete → BUDGET_FILTER
    
    5. BUDGET_FILTER:
       - Valida monthly_budget >= R$ 5.000
       - qualified → ASK_TO_SCHEDULE
       - not_qualified → FALLBACK (sem agendamento)
    
    6. ASK_TO_SCHEDULE:
       - Modo 1 (asked_to_schedule=False): Pergunta se quer agendar → END
       - Modo 2 (asked_to_schedule=True): Analisa resposta
       - yes → DATETIME_COLLECTOR
       - no → THANKYOU
       - wait → END (não entendeu, aguarda nova resposta)
    
    7. DATETIME_COLLECTOR:
       - Modo 1 (requested_datetime=None): Pergunta data/hora específica → END
       - Modo 2: Extrai e valida datetime da resposta
       - success → SLOT_CHECKER
       - wait → END (não entendeu, aguarda nova resposta)
    
    8. SLOT_CHECKER:
       - Chama get_available_slots(date, db) para verificar disponibilidade
       - Compara requested_time com slots disponíveis
       - Se não disponível, busca alternativas (slot anterior + slot posterior)
       - available → APPOINTMENT_CREATOR
       - unavailable → ALTERNATIVE_SLOTS
    
    9. ALTERNATIVE_SLOTS:
       - Modo 1 (chosen_slot=None): Oferece 2 alternativas (anterior + posterior) → END
       - Modo 2: Analisa escolha (1 ou 2) e converte para datetime
       - chosen → APPOINTMENT_CREATOR
       - wait → END (não entendeu, aguarda nova escolha)
    
    10. APPOINTMENT_CREATOR:
        - Determina datetime final (requested_datetime OU chosen_slot)
        - Cria Appointment no banco
        - Formata mensagem de confirmação
        - Sempre → CONFIRMATION
    
    11. CONFIRMATION:
        - Mensagem final de sucesso
        - Sempre → END
    
    12. FALLBACK (budget < R$ 5.000):
        - Mensagem educada informando equipe comercial entrará em contato
        - Sempre → END
    
    13. THANKYOU (não quis agendar):
        - Mensagem educada deixando porta aberta
        - Sempre → END
    """
    
    workflow = StateGraph(MarketingCRMState)
    
    # ========== REGISTRA 12 NODES ==========
    workflow.add_node("greeting", greeting_node)
    workflow.add_node("intent_analyzer", intent_analyzer_node)
    workflow.add_node("question_answerer", question_answerer_node)
    workflow.add_node("qualification_agent", qualification_agent_node)
    workflow.add_node("budget_filter", budget_filter_node)
    workflow.add_node("ask_to_schedule", ask_to_schedule_node)
    workflow.add_node("datetime_collector", datetime_collector_node)
    workflow.add_node("slot_checker", slot_checker_node)
    workflow.add_node("alternative_slots", alternative_slots_node)
    workflow.add_node("appointment_creator", appointment_creator_node)
    workflow.add_node("confirmation", confirmation_node)
    workflow.add_node("fallback", fallback_node)
    workflow.add_node("thankyou", thankyou_node)
    workflow.add_node("returning_client_handler", returning_client_handler_node)
    
    # ========== ENTRY POINT CONDICIONAL ==========
    workflow.set_conditional_entry_point(
        determine_entry_point,
        {
            "greeting": "greeting",
            "intent_analyzer": "intent_analyzer",
            "question_answerer": "question_answerer",
            "qualification_agent": "qualification_agent",
            "budget_filter": "budget_filter",
            "ask_to_schedule": "ask_to_schedule",
            "datetime_collector": "datetime_collector",
            "slot_checker": "slot_checker",
            "alternative_slots": "alternative_slots",
            "appointment_creator": "appointment_creator",
            "returning_client_handler": "returning_client_handler"
        }
    )
    
    # ========== GREETING → END ou RETURNING_CLIENT_HANDLER ==========
    # Cliente novo: END (aguarda primeira resposta)
    # Cliente retornando: encadeia direto para returning_client_handler
    def route_after_greeting(state: MarketingCRMState) -> str:
        mode = state.get("conversation_mode")
        if mode in ("returning_with_appointment", "returning_without_appointment"):
            return "returning_client_handler"
        return "__end__"
    
    workflow.add_conditional_edges(
        "greeting",
        route_after_greeting,
        {
            "returning_client_handler": "returning_client_handler",
            "__end__": END
        }
    )
    
    # ========== INTENT_ANALYZER → QUESTION_ANSWERER ou QUALIFICATION ou GREETING ==========
    workflow.add_conditional_edges(
        "intent_analyzer",
        route_after_intent,
        {
            "question": "question_answerer",
            "meeting": "qualification_agent",
            "unclear": "greeting"
        }
    )
    
    # ========== QUESTION_ANSWERER → END ==========
    # Aguarda resposta do cliente sobre permissão para qualificar
    workflow.add_edge("question_answerer", END)
    
    # ========== QUALIFICATION_AGENT → loop ou BUDGET_FILTER ==========
    workflow.add_conditional_edges(
        "qualification_agent",
        check_qualification_complete,
        {
            "continue": END,  # Aguarda próxima resposta, voltará para qualification_agent via entry point
            "complete": "budget_filter"
        }
    )
    
    # ========== BUDGET_FILTER → ASK_TO_SCHEDULE ou FALLBACK ==========
    workflow.add_conditional_edges(
        "budget_filter",
        route_after_budget,
        {
            "qualified": "ask_to_schedule",
            "not_qualified": "fallback"
        }
    )
    
    # ========== ASK_TO_SCHEDULE → DATETIME_COLLECTOR ou THANKYOU ou END ==========
    workflow.add_conditional_edges(
        "ask_to_schedule",
        route_after_ask,
        {
            "yes": "datetime_collector",
            "no": "thankyou",
            "wait": END  # Aguarda resposta mais clara
        }
    )
    
    # ========== DATETIME_COLLECTOR → SLOT_CHECKER ou END ==========
    workflow.add_conditional_edges(
        "datetime_collector",
        route_after_datetime,
        {
            "success": "slot_checker",
            "wait": END  # Aguarda data/hora válida
        }
    )
    
    # ========== SLOT_CHECKER → APPOINTMENT_CREATOR ou ALTERNATIVE_SLOTS ==========
    workflow.add_conditional_edges(
        "slot_checker",
        route_after_slot_check,
        {
            "available": "appointment_creator",
            "unavailable": "alternative_slots"
        }
    )
    
    # ========== ALTERNATIVE_SLOTS → APPOINTMENT_CREATOR ou END ==========
    workflow.add_conditional_edges(
        "alternative_slots",
        route_after_alternative,
        {
            "chosen": "appointment_creator",
            "wait": END  # Aguarda escolha válida
        }
    )
    
    # ========== APPOINTMENT_CREATOR → CONFIRMATION ==========
    workflow.add_edge("appointment_creator", "confirmation")
    
    # ========== EDGES FINAIS (todos vão para END) ==========
    workflow.add_edge("confirmation", END)
    workflow.add_edge("fallback", END)
    workflow.add_edge("thankyou", END)
    workflow.add_edge("returning_client_handler", END)  # Aguarda resposta do cliente
    
    app = workflow.compile()
    return app


marketing_crm_graph = create_marketing_crm_graph()
