import re
from langchain_core.messages import AIMessage, HumanMessage
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import asyncio

from app.agent.state import MarketingCRMState
from app.core.llm_factory import get_llm

# Timezone do Brasil
BRAZIL_TZ = ZoneInfo("America/Sao_Paulo")


async def datetime_collector_node(state: MarketingCRMState) -> dict:
    """NODE: DATETIME_COLLECTOR - Coleta data/hora desejada pelo cliente usando LLM."""
    
    requested_datetime = state.get("requested_datetime")
    
    # Se já tem data/hora extraída, pula
    if requested_datetime is not None:
        print("📅 Datetime Collector: Data/hora já extraída")
        return {
            "current_step": "datetime_collector"
        }
    
    # Pega última mensagem do usuário
    last_message = state["messages"][-1]
    user_input = last_message.content if hasattr(last_message, 'content') else str(last_message)
    last_requested_date = state.get("last_requested_date")  # Data da tentativa anterior
    
    now = datetime.now(BRAZIL_TZ)
    
    # Usa LLM para extrair data/hora
    print(f"📅 Datetime Collector: Extraindo data/hora com LLM: '{user_input}'")
    
    context = ""
    if last_requested_date:
        # Converte date para datetime se necessário
        if hasattr(last_requested_date, 'strftime'):
            context_date_str = last_requested_date.strftime('%d/%m/%Y')
            if hasattr(last_requested_date, 'hour'):
                weekday = last_requested_date.strftime('%A')
            else:
                # É um date, não datetime - converte
                from datetime import date
                if isinstance(last_requested_date, date):
                    dt = datetime.combine(last_requested_date, datetime.min.time(), tzinfo=BRAZIL_TZ)
                    weekday = dt.strftime('%A')
                else:
                    weekday = ""
            
            context = f"\n- Data da tentativa anterior: {context_date_str} ({weekday}) - SE usuário disser apenas horário (ex: '10h', 'às 14'), USE ESTA DATA"
            print(f"📅 CONTEXTO ATIVO: {context_date_str} ({weekday})")
    
    extraction_prompt = f"""Você é um assistente inteligente que extrai datas e horários de mensagens naturais.

CONTEXTO:
- Hoje é: {now.strftime('%d/%m/%Y (%A) às %H:%M')}
- Horário comercial: Segunda a Sexta, 9h-12h e 14h-18h{context}

MENSAGEM DO USUÁRIO:
"{user_input}"

INSTRUÇÕES:
1. Analise a mensagem e identifique se há intenção de agendar com data/hora específica
2. Se houver:
   - Apenas horário (ex: "quero às 10:00", "pode ser 14h") + há data anterior no contexto = OBRIGATÓRIO usar a data do contexto
   - Dias da semana (ex: "terça", "quinta") = próxima ocorrência desse dia
   - Data explícita (17/02, 18/02) = use essa data
   - Horários como "11h", "às 14", "10:00" = converta para HH:00
3. Se NÃO houver data/hora clara (ex: "quero sim", "ok", "me conta"), responda NENHUM

FORMATO DE SAÍDA (OBRIGATÓRIO):
Linha 1: RESULTADO: DD/MM/YYYY HH:MM
OU
Linha 1: RESULTADO: NENHUM

Exemplos:
"terça às 11" (sem contexto) → RESULTADO: {(now + timedelta(days=(1-now.weekday())%7 or 7)).strftime('%d/%m/%Y')} 11:00
"17/02 14h" → RESULTADO: 17/02/2026 14:00
"quero às 10:00" (contexto: 17/02/2026 terça) → RESULTADO: 17/02/2026 10:00
"pode ser 14h" (contexto: 18/02/2026 quarta) → RESULTADO: 18/02/2026 14:00
"pode ser" → RESULTADO: NENHUM
"me fala mais" → RESULTADO: NENHUM"""

    try:
        llm = get_llm()
        # Adiciona timeout de 25 segundos na chamada LLM
        response = await asyncio.wait_for(
            llm.ainvoke([HumanMessage(content=extraction_prompt)]),
            timeout=25.0
        )
        result = response.content.strip()
        
        # Procura linha "RESULTADO: ..."
        if "RESULTADO:" in result.upper():
            # Extrai apenas a linha com RESULTADO
            for line in result.split('\n'):
                if "RESULTADO:" in line.upper():
                    result = line.split(':', 1)[1].strip()
                    break
        
        if "NENHUM" in result.upper():
            print("📅 LLM não conseguiu extrair data/hora")
            return {
                "messages": [AIMessage(
                    content="Ótimo! Qual data e horário você prefere? "
                            "Atendemos Segunda a Sexta, das 9h às 12h e das 14h às 18h."
                )],
                "current_step": "datetime_collector"
            }
        
        # Parse DD/MM/YYYY HH:MM (usa search para encontrar mesmo em respostas longas)
        match = re.search(r'(\d{2})/(\d{2})/(\d{4})\s+(\d{2}):(\d{2})', result)
        if not match:
            print(f"📅 LLM retornou formato inválido: {result}")
            return {
                "messages": [AIMessage(
                    content="Desculpe, não consegui entender a data/hora. "
                            "Pode informar novamente? Ex: '18/02/2026 às 14h'"
                )],
                "current_step": "datetime_collector"
            }
        
        day, month, year, hour, minute = map(int, match.groups())
        parsed_dt = datetime(year, month, day, hour, minute, tzinfo=BRAZIL_TZ)
        
    except asyncio.TimeoutError:
        print(f"⏱️ Timeout ao chamar LLM - tentando fallback com regex")
        # Fallback: tenta regex simples para padrões óbvios
        fallback_match = re.search(r'(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\s*(?:às?|as)?\s*(\d{1,2})h?', user_input, re.IGNORECASE)
        if fallback_match:
            day, month, year, hour = fallback_match.groups()
            year = year or now.year
            if len(str(year)) == 2:
                year = 2000 + int(year)
            try:
                parsed_dt = datetime(int(year), int(month), int(day), int(hour), 0, tzinfo=BRAZIL_TZ)
                print(f"✅ Fallback regex extraiu: {parsed_dt}")
                # Continua para validações abaixo
            except:
                pass
        
        if 'parsed_dt' not in locals():
            return {
                "messages": [AIMessage(
                    content="Desculpe, demorei muito para processar. Pode repetir a data e horário? "
                            "Ex: 'terça às 14h' ou '18/02 às 10h'"
                )],
                "current_step": "datetime_collector"
            }
    except Exception as e:
        print(f"❌ Erro ao extrair data/hora com LLM: {e}")
        return {
            "messages": [AIMessage(
                content="Desculpe, tive um problema. Qual data e horário você prefere? "
                        "Ex: '18/02 às 14h'"
            )],
            "current_step": "datetime_collector"
        }
    
    # Validar horário comercial
    weekday = parsed_dt.weekday()  # 0=seg, 6=dom
    hour = parsed_dt.hour
    
    if weekday >= 5:  # sábado ou domingo
        return {
            "messages": [AIMessage(
                content="Esse dia é fim de semana. 😅 Atendemos apenas Segunda a Sexta, "
                        "das 9h às 12h e das 14h às 18h. Pode escolher outro dia?"
            )],
            "current_step": "datetime_collector"
        }
    
    if not ((9 <= hour < 12) or (14 <= hour < 18)):
        return {
            "messages": [AIMessage(
                content="Esse horário está fora do nosso expediente. "
                        "Atendemos das 9h às 12h e das 14h às 18h. Pode escolher outro horário?"
            )],
            "current_step": "datetime_collector"
        }
    
    if parsed_dt <= now:
        return {
            "messages": [AIMessage(
                content="Essa data/hora já passou. Pode escolher uma data futura?"
            )],
            "current_step": "datetime_collector"
        }
    
    print(f"📅 Datetime Collector: Extraído {parsed_dt}")
    
    return {
        "requested_datetime": parsed_dt,
        "current_step": "datetime_collector"
    }


def route_after_datetime(state: MarketingCRMState) -> str:
    """ROTEAMENTO: Verifica se conseguiu extrair data/hora válida."""
    
    requested_datetime = state.get("requested_datetime")
    
    if requested_datetime:
        print("✅ Data/hora coletada - verificando disponibilidade")
        return "success"
    else:
        print("⏳ Aguardando data/hora válida")
        return "wait"
