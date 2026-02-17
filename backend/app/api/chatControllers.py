"""
Chat Controller - API REST para interação com o agente LangGraph.

Substitui o webhook WhatsApp por endpoints REST simples,
permitindo que visitantes interajam com o agente via chat web.

Endpoints:
    POST /api/v1/chat/message  - Envia mensagem e recebe resposta do agente
    POST /api/v1/chat/reset    - Limpa sessão e reinicia conversa
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from collections import defaultdict
from asyncio import Lock, wait_for, TimeoutError
from langchain_core.messages import HumanMessage, AIMessage

from app.agent.graph import marketing_crm_graph

router = APIRouter(prefix="/chat", tags=["chat"])


# ========== STATE MANAGEMENT (in-memory por sessão) ==========

# State persistido por session_id (mesmo padrão do antigo WhatsApp handler)
user_states: dict[str, dict] = {}

# Lock por sessão para evitar race conditions
session_locks: dict[str, Lock] = defaultdict(Lock)


# ========== SCHEMAS ==========

class ChatMessageRequest(BaseModel):
    """Request para enviar mensagem ao agente."""
    session_id: str = Field(..., description="UUID da sessão do visitante", min_length=1)
    message: str = Field(..., description="Mensagem do visitante", min_length=1, max_length=2000)


class ChatMessageResponse(BaseModel):
    """Response com a resposta do agente."""
    response: str = Field(..., description="Resposta do agente")
    session_id: str = Field(..., description="ID da sessão")
    conversation_mode: Optional[str] = Field(None, description="Modo atual da conversa")


class ChatResetRequest(BaseModel):
    """Request para resetar sessão."""
    session_id: str = Field(..., description="UUID da sessão a ser resetada", min_length=1)


class ChatResetResponse(BaseModel):
    """Response da operação de reset."""
    message: str
    session_id: str


# ========== HELPERS ==========

def extract_agent_response(result: dict) -> str:
    """
    Extrai a resposta do agente do resultado do grafo.
    
    O LangGraph pode retornar a resposta em diferentes campos:
    1. final_response (campo explícito do state)
    2. Última AIMessage no histórico de messages
    3. Fallback genérico
    """
    # 1. Campo explícito
    if result.get("final_response"):
        return result["final_response"]
    
    # 2. Última AIMessage
    messages = result.get("messages", [])
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content:
            return msg.content
    
    # 3. Fallback
    return "Desculpe, não consegui processar sua mensagem. Pode tentar novamente?"


# ========== ENDPOINTS ==========

@router.post("/message", response_model=ChatMessageResponse)
async def send_message(request: ChatMessageRequest):
    """
    Envia mensagem do visitante ao agente e retorna a resposta.
    
    - Cada visitante é identificado por session_id (UUID gerado no frontend)
    - O state da conversa é mantido em memória por session_id
    - Lock por sessão garante processamento sequencial de mensagens
    """
    session_id = request.session_id
    
    # Adquirir lock para esta sessão (evita race condition)
    async with session_locks[session_id]:
        try:
            # Recuperar ou criar state
            current_state = user_states.get(session_id, {})
            
            # NÃO resetar automaticamente - mantém contexto para cancelamentos, etc
            # (comentado: auto-reset após "completed")
            # if current_state.get("conversation_mode") == "completed":
            #     current_state = {}
            
            # Adicionar mensagem do usuário ao state
            messages = current_state.get("messages", [])
            messages.append(HumanMessage(content=request.message))
            current_state["messages"] = messages
            current_state["user_input"] = request.message
            current_state["session_id"] = session_id
            
            # Invocar o grafo LangGraph com timeout de 30s
            try:
                result = await wait_for(
                    marketing_crm_graph.ainvoke(current_state),
                    timeout=60.0
                )
            except TimeoutError:
                print(f"⏱️ Timeout ao processar mensagem (session={session_id})")
                raise HTTPException(
                    status_code=504,
                    detail="Tempo limite excedido. Tente enviar sua mensagem novamente."
                )
            
            # Extrair resposta
            response_text = extract_agent_response(result)
            
            # Persistir state atualizado
            user_states[session_id] = result
            
            return ChatMessageResponse(
                response=response_text,
                session_id=session_id,
                conversation_mode=result.get("conversation_mode")
            )
            
        except Exception as e:
            print(f"❌ Erro no chat (session={session_id}): {e}")
            raise HTTPException(
                status_code=500,
                detail="Erro ao processar mensagem. Tente novamente."
            )


@router.post("/reset", response_model=ChatResetResponse)
async def reset_session(request: ChatResetRequest):
    """
    Limpa a sessão do visitante e reinicia a conversa.
    
    Remove o state em memória, permitindo que o visitante
    comece uma nova conversa do zero.
    """
    session_id = request.session_id
    
    async with session_locks[session_id]:
        # Remover state da memória
        if session_id in user_states:
            del user_states[session_id]
        
        # Remover lock (limpeza)
        if session_id in session_locks:
            del session_locks[session_id]
    
    return ChatResetResponse(
        message="Sessão resetada com sucesso. Envie uma mensagem para começar nova conversa.",
        session_id=session_id
    )
