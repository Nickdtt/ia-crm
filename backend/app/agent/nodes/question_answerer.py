import re

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from app.core.llm_factory import get_llm
from app.agent.state import MarketingCRMState
from app.rag import search_documents


QUESTION_ANSWERER_PROMPT = """Você é o agente virtual da "Isso não é uma agência", estúdio de crescimento digital.

O cliente fez uma pergunta. Use o CONTEXTO abaixo (extraído dos documentos da empresa) para responder com precisão.

REGRAS:
- Responda de forma OBJETIVA (máximo 3-4 linhas)
- Use APENAS informações do contexto fornecido — não invente dados
- Se o contexto não contiver a resposta, diga que pode verificar e ofereça a consultoria gratuita
- Pode mencionar valores e planos SE estiverem no contexto
- Pode citar cases de sucesso SE estiverem no contexto
- SEM pressionar, seja consultivo e natural

{permission_instruction}

CONTEXTO DOS DOCUMENTOS:
{rag_context}"""


# ========== HELPERS DE DETECÇÃO ==========

EMAIL_REGEX = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')


def _detect_email(text: str) -> str | None:
    """Detecta email via regex."""
    match = EMAIL_REGEX.search(text)
    return match.group(0).lower() if match else None


def _detect_name(text: str) -> str | None:
    """Detecta nome completo (2+ palavras alfabéticas).
    
    Exclui respostas comuns que não são nomes.
    """
    cleaned = text.strip().lower()
    
    # Rejeita se contém caracteres especiais ou números
    if '?' in cleaned or '@' in cleaned or any(c.isdigit() for c in cleaned):
        return None
    
    # Palavras que indicam NÃO é nome (respostas comuns)
    reject_patterns = [
        'não', 'nao', 'agora não', 'agora nao', 'ainda não', 'ainda nao',
        'depois', 'talvez', 'sem tempo', 'mais tarde', 'tenho pressa',
        'só quero', 'quero saber', 'me fala', 'pode ser', 'obrigado',
        'por favor', 'com certeza', 'claro', 'sim', 'ok'
    ]
    
    if any(pattern in cleaned for pattern in reject_patterns):
        return None
    
    words = text.strip().split()
    
    # 2-5 palavras, todas alfabéticas (permite acentos)
    if 2 <= len(words) <= 5 and all(re.match(r'^[a-zA-ZÀ-ÿ]+$', w) for w in words):
        return text.strip().title()
    
    return None


async def question_answerer_node(state: MarketingCRMState) -> dict:
    """NODE: QUESTION_ANSWERER - Responde pergunta com RAG.
    
    MODO 1: Primeira vez (permission_asked=False) → responde pergunta
    MODO 2: Já respondeu → analisa resposta:
        - Se detecta intenção de agendamento → roteia para lead collection
        - Dados forn./aceitou → seta permission_granted + extrai dados + roteia
        - Recusou → responde com RAG SEM re-pedir permissão
        - Nova pergunta → responde com RAG
    """
    
    last_message = state["messages"][-1]
    user_input = last_message.content if hasattr(last_message, 'content') else str(last_message)
    permission_asked = state.get("permission_asked", False)
    permission_granted = state.get("permission_granted")
    llm = get_llm()
    
    # --- Detecção de intenção de agendamento via LLM ---
    intent_prompt = f"""Analise esta mensagem do usuário:

"{user_input}"

O usuário quer agendar/marcar uma reunião/consultoria?
Palavras-chave: "quero", "agendar", "marcar", "reunião", "consultoria", etc.

Responda APENAS: SIM ou NAO"""

    try:
        intent_response = await llm.ainvoke([HumanMessage(content=intent_prompt)])
        has_scheduling_intent = "sim" in intent_response.content.strip().lower()
    except:
        has_scheduling_intent = False
    
    if has_scheduling_intent:
        print(f"🎯 Question Answerer: Detectou intenção de agendamento → indo para lead collection")
        return {
            "permission_granted": True,
            "messages": [AIMessage(content="Perfeito! Vou te ajudar com isso. Primeiro, qual é o seu nome completo?")],
            "current_step": "lead_collector"
        }
    
    # MODO 2: Já pediu permissão — analisar resposta do usuário
    if permission_asked and permission_granted is None:
        
        # --- Detecção rápida de email (regex é confiável aqui) ---
        detected_email = _detect_email(user_input)
        
        # --- Detecção de nome via LLM (mais confiável) ---
        detected_name = None
        if not detected_email and len(user_input.split()) <= 5:
            name_prompt = f"""A mensagem abaixo é um NOME COMPLETO de pessoa?

"{user_input}"

Responda:
- Se for nome completo (2+ palavras): SIM|Nome Formatado
- Se não for nome: NAO

Exemplos:
- "Nicolas Figueiredo" → SIM|Nicolas Figueiredo
- "me conte" → NAO
- "quero reuniao" → NAO"""

            try:
                name_response = await llm.ainvoke([HumanMessage(content=name_prompt)])
                result = name_response.content.strip()
                if result.startswith("SIM|"):
                    detected_name = result.split("|")[1].strip()
                    print(f"✅ Question Answerer: Nome detectado via LLM '{detected_name}'")
            except:
                pass
        
        if detected_name:
            # Usuário já mandou o nome → salvar + confirmar + pedir email
            return {
                "permission_granted": True,
                "lead_name": detected_name,
                "messages": [AIMessage(content=f"Prazer, {detected_name.split()[0]}! Qual é o seu email?")],
                "current_step": "lead_collector"
            }
        
        if detected_email:
            # Usuário mandou email → salvar + confirmar + pedir nome
            return {
                "permission_granted": True,
                "lead_email": detected_email,
                "messages": [AIMessage(content=f"Anotei! Qual é o seu nome completo?")],
                "current_step": "lead_collector"
            }
        
        # --- Detecção via LLM: aceite explícito ---
        
        analysis_prompt = f"""Analise esta resposta do usuário:

Mensagem: "{user_input}"

Contexto: Perguntamos se podíamos fazer algumas perguntas para entender o negócio dele.

O usuário ACEITOU? ("sim", "pode", "claro", "ok", "vamos lá" = SIM)
Ou RECUSOU / fez outra pergunta? ("não", "agora não", pergunta nova = NAO)

Responda APENAS: SIM ou NAO"""
        
        analysis = await llm.ainvoke([HumanMessage(content=analysis_prompt)])
        accepted = "sim" in analysis.content.strip().lower()
        
        if accepted:
            print(f"✅ Question Answerer: Usuário ACEITOU explicitamente")
            return {
                "permission_granted": True,
                "messages": [AIMessage(content="Ótimo! Vamos lá então. Qual é o seu nome completo?")],
                "current_step": "lead_collector"
            }
        
        # --- Recusou ou fez outra pergunta → responder com RAG SEM re-pedir ---
        print(f"ℹ️ Question Answerer: Usuário RECUSOU ou fez nova pergunta → respondendo SEM insistir")
        
        rag_results = search_documents(user_input, top_k=3)
        rag_context = "\n\n---\n\n".join(rag_results) if rag_results else "(Nenhum documento relevante encontrado)"
        
        prompt = QUESTION_ANSWERER_PROMPT.format(
            rag_context=rag_context,
            permission_instruction="Responda apenas a pergunta. NÃO peça permissão para fazer perguntas. Seja prestativo e deixe o cliente no controle da conversa."
        )
        
        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=f'Pergunta do cliente: "{user_input}"\n\nSua resposta:')
        ]
        
        try:
            response = await llm.ainvoke(messages)
            answer = response.content
        except Exception as e:
            print(f"❌ Erro: {type(e).__name__}: {e}")
            answer = "Entendo. Estou aqui se precisar de mais alguma informação! 😊"
        
        return {
            "messages": [AIMessage(content=answer)],
            "current_step": "question_answerer"
        }
    
    # MODO 1: Primeira resposta — RAG simples (sem pedir permissão automaticamente)
    rag_results = search_documents(user_input, top_k=3)
    
    if rag_results:
        rag_context = "\n\n---\n\n".join(rag_results)
        print(f"📚 RAG: {len(rag_results)} chunks encontrados para: '{user_input[:50]}...'")
    else:
        rag_context = "(Nenhum documento relevante encontrado)"
        print(f"📚 RAG: nenhum resultado para: '{user_input[:50]}...'")
    
    prompt = QUESTION_ANSWERER_PROMPT.format(
        rag_context=rag_context,
        permission_instruction="Responda a pergunta de forma objetiva e prestativa. Seja disponível mas não insistente. Se o cliente demonstrar interesse em saber mais ou agendar algo, aí sim você pode se oferecer para ajudar."
    )
    
    llm = get_llm()
    
    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content=f'Pergunta do cliente: "{user_input}"\n\nSua resposta:')
    ]
    
    try:
        response = await llm.ainvoke(messages)
        answer = response.content
    except Exception as e:
        print(f"❌ Erro ao responder pergunta com LLM: {type(e).__name__}: {e}")
        answer = "Nós construímos sistemas de aquisição de clientes — não somos uma agência tradicional. Posso te contar mais sobre como funcionamos! 😊"
    
    print(f"💬 Question Answerer: Respondeu com RAG (sem pressionar)")
    
    return {
        "messages": [AIMessage(content=answer)],
        "permission_asked": True,
        "conversation_mode": "qualification",
        "current_step": "question_answerer"
    }
