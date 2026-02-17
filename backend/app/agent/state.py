from typing import Annotated, Literal
from langgraph.graph import MessagesState
from uuid import UUID
from decimal import Decimal
from datetime import datetime


class MarketingCRMState(MessagesState):
    """
    Estado do grafo de agendamento da Isso não é uma agência.
    
    MessagesState fornece:
    - messages: list[BaseMessage] - Histórico da conversa
    
    Campos customizados para fluxo conversacional + qualificação + agendamento.
    """
    
    # ========== CONTROLE DE FLUXO ==========
    conversation_mode: Annotated[
        Literal[
            "idle",                            # Aguardando primeira interação
            "qualification",                   # Coletando dados do cliente
            "scheduling",                      # Processo de agendamento (data/hora/confirmação)
            "question",                        # Respondendo pergunta do cliente
            "completed",                       # Conversa finalizada
            "returning_with_appointment",      # Cliente retornando (tem appointment)
            "returning_without_appointment",   # Cliente retornando (sem appointment)
            "requalification"                  # Revalidando dados de cliente existente
        ] | None,
        "Modo atual da conversa - usado para entry point dinâmico"
    ] = None
    
    current_step: Annotated[
        str | None,
        "Node atual (para debug e logs)"
    ] = None
    
    
    # ========== APRESENTAÇÃO E INTENÇÃO INICIAL ==========
    presentation_done: Annotated[
        bool,
        "Se já se apresentou como agente virtual da Isso não é uma agência"
    ] = False
    
    initial_intent_captured: Annotated[
        bool,
        "Se já capturou a intenção inicial do cliente"
    ] = False
    
    initial_intent: Annotated[
        Literal["wants_meeting", "has_question", "unknown"] | None,
        """Intenção na primeira resposta:
        - wants_meeting: Quer agendar reunião
        - has_question: Tem dúvida/pergunta
        - unknown: Não identificado
        """
    ] = None
    
    
    # ========== QUALIFICAÇÃO ==========
    permission_asked: Annotated[
        bool,
        "Se já pediu permissão para coletar dados"
    ] = False
    
    permission_granted: Annotated[
        bool | None,
        "Se o usuário aceitou responder perguntas (None=ainda não respondeu, True=aceitou, False=recusou)"
    ] = None
    
    
    # ========== DADOS DO LEAD (Coleta Simplificada - Portfolio) ==========
    lead_name: Annotated[
        str | None,
        "Nome completo do lead (2-3 campos coletados)"
    ] = None
    
    lead_email: Annotated[
        str | None,
        "Email do lead"
    ] = None
    
    lead_interest: Annotated[
        str | None,
        "Interesse/necessidade principal descrito pelo lead"
    ] = None
    
    lead_collection_complete: Annotated[
        bool,
        "Se os 3 campos mínimos foram coletados (nome, email, interesse)"
    ] = False
    
    phone: Annotated[
        str | None,
        "Telefone gerado automaticamente como web-{session_id[:8]} ou fornecido pelo lead"
    ] = None
    
    client_data: Annotated[
        dict | None,
        """Dados coletados (LEGACY - mantido para compatibilidade):
        - full_name (separado em first_name + last_name)
        - email (opcional)
        - segment, main_marketing_problem
        - monthly_budget
        """
    ] = None
    
    client_id: Annotated[
        UUID | None,
        "ID do cliente criado no banco"
    ] = None
    
    qualification_complete: Annotated[
        bool,
        "Se todos dados foram coletados"
    ] = False
    
    
    # ========== VALIDAÇÃO DE BUDGET ==========
    budget_qualified: Annotated[
        bool,
        "Se orçamento >= R$ 5.000"
    ] = False
    
    
    # ========== AGENDAMENTO ==========
    asked_to_schedule: Annotated[
        bool,
        "Se já perguntou se cliente quer agendar"
    ] = False
    
    wants_to_schedule: Annotated[
        bool | None,
        """Resposta sobre agendamento:
        - True: Quer agendar
        - False: Não quer
        - None: Não respondeu
        """
    ] = None
    
    requested_datetime: Annotated[
        datetime | None,
        "Data/hora solicitada pelo cliente"
    ] = None
    
    last_requested_date: Annotated[
        datetime | None,
        "Data da última tentativa de agendamento (usado quando slot indisponível)"
    ] = None
    
    slot_available: Annotated[
        bool | None,
        """Disponibilidade do slot:
        - True: Disponível
        - False: Indisponível
        - None: Não verificou
        """
    ] = None
    
    alternative_slots: Annotated[
        dict | None,
        """Slots alternativos:
        - previous: slot anterior
        - next: slot posterior
        """
    ] = None
    
    chosen_slot: Annotated[
        datetime | None,
        "Slot escolhido após alternativas"
    ] = None
    
    appointment_confirmed: Annotated[
        bool,
        "Se appointment foi criado no banco"
    ] = False
    
    appointment_id: Annotated[
        UUID | None,
        "ID do appointment criado"
    ] = None
    
    
    # ========== SESSÃO E CONTEXTO ==========
    session_id: Annotated[
        str | None,
        "ID da sessão do WhatsApp (phone number do cliente)"
    ] = None
    
    final_response: Annotated[
        str | None,
        "Mensagem final formatada para enviar ao cliente"
    ] = None
