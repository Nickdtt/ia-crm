"""Nó simplificado de coleta de lead — portfolio version.

Coleta 3 campos com extração determinística (regex):
1. Nome completo (2+ palavras alfabéticas)
2. Email (regex)
3. Interesse/necessidade principal (qualquer frase > 10 chars)

Usa 1 única chamada LLM para gerar a resposta conversacional.
Telefone gerado automaticamente como web-{session_id[:8]}.
"""

import re

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from app.core.llm_factory import get_llm
from app.agent.state import MarketingCRMState


EMAIL_REGEX = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')


def _extract_email(text: str) -> str | None:
    match = EMAIL_REGEX.search(text)
    return match.group(0).lower() if match else None


def _extract_name(text: str) -> str | None:
    """Detecta nome (2-5 palavras alfabéticas, sem '?' ou '@')."""
    cleaned = text.strip().lower()
    
    if '?' in cleaned or '@' in cleaned:
        return None
    
    # Rejeita palavras que não são nomes
    reject_patterns = [
        'não', 'nao', 'quero', 'reuniao', 'reunião', 'consultoria',
        'agendar', 'marcar', 'depois', 'talvez', 'pode ser',
        'obrigado', 'por favor', 'claro', 'sim', 'ok'
    ]
    
    if any(pattern in cleaned for pattern in reject_patterns):
        return None
    
    words = text.strip().split()
    if 2 <= len(words) <= 5 and all(re.match(r'^[a-zA-Z\u00C0-\u017F]+$', w) for w in words):
        return text.strip().title()
    return None


def _extract_interest(text: str) -> str | None:
    """Detecta interesse (frase com 15+ chars que não é nome/email)."""
    cleaned = text.strip()
    if '@' in cleaned:
        return None
    words = cleaned.split()
    if len(words) < 3:
        return None
    if len(cleaned) >= 15:
        return cleaned
    return None


async def simple_lead_collector_node(state: MarketingCRMState) -> dict:
    """Coleta lead simplificada: nome + email + interesse.
    
    Extração determinística (regex) + 1 única chamada LLM para resposta.
    """
    
    last_message = state["messages"][-1]
    user_input = last_message.content if hasattr(last_message, 'content') else str(last_message)
    
    # Estado atual dos campos
    has_name = bool(state.get("lead_name"))
    has_email = bool(state.get("lead_email"))
    has_interest = bool(state.get("lead_interest"))
    
    updates: dict = {}
    
    # ========== EXTRAÇÃO DETERMINÍSTICA ==========
    # Tenta extrair o campo que está faltando da mensagem atual
    
    if not has_name:
        name = _extract_name(user_input)
        if name:
            updates["lead_name"] = name
            has_name = True
            print(f"📝 Lead nome capturado: {name}")
    
    if not has_email:
        email = _extract_email(user_input)
        if email:
            updates["lead_email"] = email
            has_email = True
            print(f"📧 Lead email capturado: {email}")
    
    if not has_interest:
        interest = _extract_interest(user_input)
        if interest:
            updates["lead_interest"] = interest
            has_interest = True
            print(f"💡 Lead interesse capturado: {interest}")
    
    # ========== VERIFICAR SE COMPLETO ==========
    # Atualiza has_* com valores do state para verificação correta
    has_name = has_name or bool(state.get("lead_name"))
    has_email = has_email or bool(state.get("lead_email"))
    has_interest = has_interest or bool(state.get("lead_interest"))
    
    if has_name and has_email and has_interest:
        final_name = state.get("lead_name", "")
        first = final_name.split()[0] if final_name else ""
        
        updates["conversation_mode"] = "scheduling"
        updates["lead_collection_complete"] = True
        # NÃO seta asked_to_schedule ainda - precisa da resposta do usuário
        updates["current_step"] = "ask_to_schedule"
        updates["messages"] = [AIMessage(
            content=f"Perfeito, {first}! Tenho tudo que preciso. 🎉"
        )]
        print("✅ Lead completo → oferecendo agendamento")
        return updates
    
    # ========== GERAR RESPOSTA ==========
    # Se acabou de capturar algum dado nesta rodada, usa resposta simples sem LLM
    
    if updates.get("lead_name") or updates.get("lead_email") or updates.get("lead_interest"):
        # Acabou de capturar algo - pergunta o PRÓXIMO campo que falta
        if not has_email:
            updates["messages"] = [AIMessage(content="Ótimo! E qual é o seu email?")]
        elif not has_interest:
            updates["messages"] = [AIMessage(content="Perfeito! Agora me conta, qual é o seu principal interesse ou necessidade?")]
        else:
            # Não deveria chegar aqui se a verificação de completo está correta
            updates["messages"] = [AIMessage(content="Entendi! Só mais uma coisa...")]
        
        updates["current_step"] = "lead_collector"
        return updates
    
    # Se não capturou nada, usa LLM para entender e redirecionar
    collected = []
    if has_name:
        collected.append(f"✓ Nome: {state.get('lead_name')}")
    if has_email:
        collected.append(f"✓ Email: {state.get('lead_email')}")
    if has_interest:
        collected.append(f"✓ Interesse: {state.get('lead_interest')}")
    
    collected_str = "\n".join(collected) if collected else "(nenhum)"
    
    # Próximo campo
    if not has_name:
        ask_for = "Confirme a informação recebida (se houver) e pergunte o NOME COMPLETO do lead."
    elif not has_email:
        ask_for = "Confirme a informação recebida (se houver) e pergunte o EMAIL do lead."
    else:
        ask_for = "Confirme a informação recebida (se houver) e pergunte qual o principal INTERESSE ou NECESSIDADE do lead."
    
    prompt = f"""Você é o agente virtual da "Isso não é uma agência".

Coletando dados para oferecer consultoria gratuita.

CAMPOS COLETADOS:
{collected_str}

INSTRUÇÃO:
{ask_for}

REGRAS:
- Seja breve (máximo 2 linhas)
- Tom natural e amigável
- NÃO repita dados que já tem
- Se o usuário mandou algo que NÃO é o campo esperado, agradeça e redirecione"""
    
    llm = get_llm()
    
    try:
        response = await llm.ainvoke([
            SystemMessage(content=prompt),
            HumanMessage(content=f'Mensagem do lead: "{user_input}"\n\nSua resposta:')
        ])
        updates["messages"] = [AIMessage(content=response.content)]
    except Exception as e:
        print(f"❌ Erro no lead collector: {type(e).__name__}: {e}")
        # Fallback sem LLM
        if not has_name:
            updates["messages"] = [AIMessage(content="Para começarmos, qual é o seu nome completo?")]
        elif not has_email:
            updates["messages"] = [AIMessage(content="Qual é o seu email?")]
        else:
            updates["messages"] = [AIMessage(content="O que você procura? Qual sua principal necessidade?")]
    
    updates["current_step"] = "lead_collector"
    return updates
