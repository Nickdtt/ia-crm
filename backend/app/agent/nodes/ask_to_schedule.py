"""Nó ask_to_schedule — pergunta se quer agendar e analisa resposta.

Zero chamadas LLM: mensagem fixa + detecção determinística SIM/NÃO.
"""

import re

from langchain_core.messages import AIMessage
from typing import Literal

from app.agent.state import MarketingCRMState


# Palavras que indicam SIM
_YES_PATTERNS = re.compile(
    r'\b(sim|quero|claro|bora|vamos|pode|gostaria|agendar|marcar|aceito|ok|com certeza|por favor)\b',
    re.IGNORECASE
)

# Palavras que indicam NÃO
_NO_PATTERNS = re.compile(
    r'\b(não|nao|agora não|agora nao|depois|talvez|ainda não|ainda nao|obrigado mas|no momento)\b',
    re.IGNORECASE
)


def _detect_wants_to_schedule(text: str) -> bool | None:
    """Detecta se o usuário quer agendar. Retorna True/False/None."""
    has_yes = bool(_YES_PATTERNS.search(text))
    has_no = bool(_NO_PATTERNS.search(text))
    
    if has_no and not has_yes:
        return False
    if has_yes and not has_no:
        return True
    if has_no and has_yes:
        # Ambíguo — "não" tem prioridade (conservador)
        return False
    return None


async def ask_to_schedule_node(state: MarketingCRMState) -> dict:
    """NODE: ASK_TO_SCHEDULE - Pergunta se quer agendar OU analisa resposta."""
    
    asked_to_schedule = state.get("asked_to_schedule", False)
    
    # MODO 1: Ainda não perguntou — mensagem fixa
    if not asked_to_schedule:
        print("📅 Ask to Schedule: Perguntando sobre agendamento")
        
        return {
            "messages": [AIMessage(
                content="Perfeito! Quer agendar uma reunião (30-40 min, Google Meet) "
                        "para discutirmos como podemos ajudar sua empresa a alcançar seus objetivos?"
            )],
            "asked_to_schedule": True,
            "conversation_mode": "scheduling",
            "current_step": "ask_to_schedule"
        }
    
    # MODO 2: Já perguntou — analisa resposta com regex
    last_message = state["messages"][-1]
    user_input = last_message.content if hasattr(last_message, 'content') else str(last_message)
    
    wants = _detect_wants_to_schedule(user_input)
    
    if wants is None:
        # Não conseguiu detectar — assume SIM (otimista, pois já está no fluxo)
        wants = True
    
    print(f"📅 Ask to Schedule: Cliente quer agendar? {wants}")
    
    return {
        "wants_to_schedule": wants,
        "current_step": "ask_to_schedule"
    }


def route_after_ask(state: MarketingCRMState) -> Literal["yes", "no", "wait"]:
    """ROTEAMENTO: Decide baseado em wants_to_schedule."""
    
    wants_to_schedule = state.get("wants_to_schedule")
    
    if wants_to_schedule is True:
        print("✅ Cliente quer agendar - coletando data/hora")
        return "yes"
    elif wants_to_schedule is False:
        print("❌ Cliente não quer agendar - finalizando")
        return "no"
    else:
        print("⏳ Aguardando resposta sobre agendamento")
        return "wait"
