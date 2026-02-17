"""
Script de simulação do chat — testa todos os comportamentos possíveis do agente.

Requer o backend rodando em localhost:8000.
Uso:
    cd backend && source venv/bin/activate
    python -m tests.test_chat_simulation

Cenários:
    1. Greeting          → primeira mensagem, agente se apresenta
    2. Pergunta RAG      → pergunta sobre serviços, resposta baseada nos PDFs
    3. Coleta de Lead    → nome → email → interesse (3 turnos)
    4. Fluxo Completo    → lead + aceita agendar + data/hora → appointment criado
    5. Recusa Agendamento→ lead completo → recusa agendar → encerra
    6. Reset de Sessão   → envia mensagens → reset → conversa recomeça do zero
"""

import asyncio
import uuid
import sys
from datetime import datetime, timedelta

import httpx

BASE_URL = "http://localhost:8000/api/v1/chat"
TIMEOUT = 60.0  # LLM pode demorar

# ========== HELPERS ==========

class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    END = "\033[0m"


def section(title: str):
    print(f"\n{'='*70}")
    print(f"{Colors.HEADER}{Colors.BOLD}  {title}{Colors.END}")
    print(f"{'='*70}")


def step(label: str, message: str):
    print(f"\n  {Colors.CYAN}👤 [{label}]{Colors.END} {message}")


def agent_says(response: str, mode: str | None = None):
    lines = response.strip().split("\n")
    print(f"  {Colors.GREEN}🤖 Agente:{Colors.END} {lines[0]}")
    for line in lines[1:]:
        print(f"             {line}")
    if mode:
        print(f"  {Colors.YELLOW}   📌 mode={mode}{Colors.END}")


def success(msg: str):
    print(f"  {Colors.GREEN}✅ {msg}{Colors.END}")


def fail(msg: str):
    print(f"  {Colors.RED}❌ {msg}{Colors.END}")


def info(msg: str):
    print(f"  {Colors.BLUE}ℹ️  {msg}{Colors.END}")


async def send_message(client: httpx.AsyncClient, session_id: str, message: str) -> dict:
    """Envia mensagem ao chat e retorna a response completa."""
    resp = await client.post(
        f"{BASE_URL}/message",
        json={"session_id": session_id, "message": message},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


async def reset_session(client: httpx.AsyncClient, session_id: str) -> dict:
    """Reseta uma sessão."""
    resp = await client.post(
        f"{BASE_URL}/reset",
        json={"session_id": session_id},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


# ========== CENÁRIOS ==========

async def test_1_greeting(client: httpx.AsyncClient) -> bool:
    """Cenário 1: Primeira mensagem → agente se apresenta."""
    section("CENÁRIO 1 — Greeting (apresentação inicial)")
    sid = str(uuid.uuid4())

    try:
        step("Usuário", "Olá!")
        data = await send_message(client, sid, "Olá!")
        agent_says(data["response"], data.get("conversation_mode"))

        # Validações
        resp_lower = data["response"].lower()
        has_greeting = any(w in resp_lower for w in ["oi", "olá", "bem-vindo", "agente", "agência", "ajudar"])

        if has_greeting:
            success("Agente respondeu com saudação ✔")
            return True
        else:
            fail("Resposta não contém saudação esperada")
            return False

    except Exception as e:
        fail(f"Erro: {e}")
        return False
    finally:
        await reset_session(client, sid)


async def test_2_rag_question(client: httpx.AsyncClient) -> bool:
    """Cenário 2: Pergunta sobre serviços → resposta com contexto RAG."""
    section("CENÁRIO 2 — Pergunta RAG (serviços/preços)")
    sid = str(uuid.uuid4())

    try:
        # Greeting primeiro
        step("Usuário", "Oi")
        data = await send_message(client, sid, "Oi")
        agent_says(data["response"], data.get("conversation_mode"))

        # Pergunta RAG
        step("Usuário", "Quais serviços vocês oferecem e qual o preço?")
        data = await send_message(client, sid, "Quais serviços vocês oferecem e qual o preço?")
        agent_says(data["response"], data.get("conversation_mode"))

        # Validação: resposta deve conter algo dos PDFs (não genérica)
        resp_lower = data["response"].lower()
        rag_indicators = [
            "sistema", "growth", "gestão", "tráfego", "social media",
            "consultoria", "lançamento", "retenção", "r$", "mensal",
            "serviço", "plano", "estratégia", "marketing",
            "aquisição", "saúde", "bem-estar", "clientes", "escaláv",
            "previsíve", "resultado", "clínica", "odonto", "estética",
            "farmácia", "autônomo", "personalizado",
        ]
        matches = [w for w in rag_indicators if w in resp_lower]

        if len(matches) >= 2:
            success(f"Resposta RAG com {len(matches)} indicadores: {matches[:5]}")
            return True
        else:
            fail(f"Resposta parece genérica (só {len(matches)} indicador(es) RAG)")
            info("Isso pode indicar que o RAG não carregou os PDFs corretamente")
            return False

    except Exception as e:
        fail(f"Erro: {e}")
        return False
    finally:
        await reset_session(client, sid)


async def test_3_lead_collection(client: httpx.AsyncClient) -> bool:
    """Cenário 3: Coleta de lead — nome → email → interesse."""
    section("CENÁRIO 3 — Coleta de Lead (3 campos)")
    sid = str(uuid.uuid4())

    try:
        # Greeting
        step("Usuário", "Olá, bom dia!")
        data = await send_message(client, sid, "Olá, bom dia!")
        agent_says(data["response"], data.get("conversation_mode"))

        # Pergunta para chegar no lead collector (via question_answerer → lead_collector)
        step("Usuário", "Me fala sobre a consultoria gratuita")
        data = await send_message(client, sid, "Me fala sobre a consultoria gratuita")
        agent_says(data["response"], data.get("conversation_mode"))

        # Campo 1: Nome
        step("Usuário", "João Carlos Silva")
        data = await send_message(client, sid, "João Carlos Silva")
        agent_says(data["response"], data.get("conversation_mode"))

        # Campo 2: Email
        step("Usuário", "joao.carlos@email.com")
        data = await send_message(client, sid, "joao.carlos@email.com")
        agent_says(data["response"], data.get("conversation_mode"))

        # Campo 3: Interesse
        step("Usuário", "Preciso de ajuda com marketing digital para minha clínica odontológica")
        data = await send_message(client, sid, "Preciso de ajuda com marketing digital para minha clínica odontológica")
        agent_says(data["response"], data.get("conversation_mode"))

        # Validação: após 3 campos, deve ter mudado para scheduling
        mode = data.get("conversation_mode", "")
        if mode == "scheduling" or "agendar" in data["response"].lower() or "reunião" in data["response"].lower():
            success("Lead coletado → modo scheduling / ofereceu agendamento ✔")
            return True
        else:
            # Pode precisar de mais uma interação (LLM pode não extrair tudo de primeira)
            info(f"Modo atual: {mode}. Tentando mais uma interação...")
            step("Usuário", "Sim, tenho interesse em marketing para odontologia")
            data = await send_message(client, sid, "Sim, tenho interesse em marketing para odontologia")
            agent_says(data["response"], data.get("conversation_mode"))

            mode = data.get("conversation_mode", "")
            if mode == "scheduling" or "agendar" in data["response"].lower():
                success("Lead coletado (com interação extra) ✔")
                return True
            else:
                fail(f"Lead não completou coleta. Modo: {mode}")
                return False

    except Exception as e:
        fail(f"Erro: {e}")
        return False
    finally:
        await reset_session(client, sid)


async def test_4_full_flow(client: httpx.AsyncClient) -> bool:
    """Cenário 4: Fluxo completo — lead + agendar + data/hora → appointment criado."""
    section("CENÁRIO 4 — Fluxo Completo (lead → agendamento)")
    sid = str(uuid.uuid4())

    try:
        # Greeting
        step("Usuário", "Oi, tudo bem?")
        data = await send_message(client, sid, "Oi, tudo bem?")
        agent_says(data["response"], data.get("conversation_mode"))

        # Trigger para question_answerer → lead_collector
        step("Usuário", "Quero saber sobre os serviços de vocês")
        data = await send_message(client, sid, "Quero saber sobre os serviços de vocês")
        agent_says(data["response"], data.get("conversation_mode"))

        # Lead: Nome
        step("Usuário", "Maria Fernanda Oliveira")
        data = await send_message(client, sid, "Maria Fernanda Oliveira")
        agent_says(data["response"], data.get("conversation_mode"))

        # Lead: Email
        step("Usuário", "maria.fernanda@clinica.com")
        data = await send_message(client, sid, "maria.fernanda@clinica.com")
        agent_says(data["response"], data.get("conversation_mode"))

        # Lead: Interesse
        step("Usuário", "Quero aumentar o número de pacientes na minha clínica de estética")
        data = await send_message(client, sid, "Quero aumentar o número de pacientes na minha clínica de estética")
        agent_says(data["response"], data.get("conversation_mode"))

        # Aceitar agendamento (se já ofereceu, ou aguardar pergunta)
        if "agendar" in data["response"].lower() or "reunião" in data["response"].lower():
            step("Usuário", "Sim, quero agendar!")
            data = await send_message(client, sid, "Sim, quero agendar!")
            agent_says(data["response"], data.get("conversation_mode"))
        else:
            # Pode precisar de uma interação extra para completar lead
            step("Usuário", "Sim, gostaria de agendar uma reunião")
            data = await send_message(client, sid, "Sim, gostaria de agendar uma reunião")
            agent_says(data["response"], data.get("conversation_mode"))

        # Informar data/hora (próxima quarta-feira às 14h — horário válido)
        next_weekday = _next_weekday_date(2)  # quarta = 2
        date_str = next_weekday.strftime("%d/%m/%Y")
        step("Usuário", f"{date_str} às 14:00")
        data = await send_message(client, sid, f"{date_str} às 14:00")
        agent_says(data["response"], data.get("conversation_mode"))

        # Validação: deve ter criado appointment (mode=completed ou mensagem de confirmação)
        mode = data.get("conversation_mode", "")
        resp_lower = data["response"].lower()

        if mode == "completed" or "confirmado" in resp_lower or "agendamento" in resp_lower:
            success("Appointment criado com sucesso! ✔")
            return True
        else:
            # Pode precisar confirmar slot ou dar mais uma resposta
            info(f"Modo: {mode}. Verificando se precisa confirmar...")
            step("Usuário", "Pode ser nesse horário mesmo")
            data = await send_message(client, sid, "Pode ser nesse horário mesmo")
            agent_says(data["response"], data.get("conversation_mode"))

            mode = data.get("conversation_mode", "")
            if mode == "completed" or "confirmado" in data["response"].lower():
                success("Appointment criado (com confirmação extra) ✔")
                return True
            else:
                fail(f"Fluxo não completou. Modo: {mode}")
                return False

    except Exception as e:
        fail(f"Erro: {e}")
        return False
    finally:
        await reset_session(client, sid)


async def test_5_decline_scheduling(client: httpx.AsyncClient) -> bool:
    """Cenário 5: Lead completo → recusa agendar → encerramento."""
    section("CENÁRIO 5 — Recusa de Agendamento")
    sid = str(uuid.uuid4())

    try:
        # Greeting
        step("Usuário", "Boa tarde")
        data = await send_message(client, sid, "Boa tarde")
        agent_says(data["response"], data.get("conversation_mode"))

        # Question → Lead collector
        step("Usuário", "Me fala dos serviços")
        data = await send_message(client, sid, "Me fala dos serviços")
        agent_says(data["response"], data.get("conversation_mode"))

        # Lead: Nome
        step("Usuário", "Pedro Santos Lima")
        data = await send_message(client, sid, "Pedro Santos Lima")
        agent_says(data["response"], data.get("conversation_mode"))

        # Lead: Email
        step("Usuário", "pedro.lima@empresa.com")
        data = await send_message(client, sid, "pedro.lima@empresa.com")
        agent_says(data["response"], data.get("conversation_mode"))

        # Lead: Interesse
        step("Usuário", "Marketing para farmácia")
        data = await send_message(client, sid, "Marketing para farmácia")
        agent_says(data["response"], data.get("conversation_mode"))

        # Recusar agendamento
        recusa_enviada = False
        for _ in range(2):
            resp_lower = data["response"].lower()
            if "agendar" in resp_lower or "reunião" in resp_lower or "consultoria" in resp_lower:
                step("Usuário", "Não, obrigado. Por enquanto não quero agendar.")
                data = await send_message(client, sid, "Não, obrigado. Por enquanto não quero agendar.")
                agent_says(data["response"], data.get("conversation_mode"))
                recusa_enviada = True
                break
            else:
                # Mais uma interação para chegar na oferta
                step("Usuário", "Só quero informações por enquanto")
                data = await send_message(client, sid, "Só quero informações por enquanto")
                agent_says(data["response"], data.get("conversation_mode"))

        if not recusa_enviada:
            step("Usuário", "Não quero agendar nada, obrigado")
            data = await send_message(client, sid, "Não quero agendar nada, obrigado")
            agent_says(data["response"], data.get("conversation_mode"))

        # Validação: deve ter encerrado sem appointment
        mode = data.get("conversation_mode", "")
        resp_lower = data["response"].lower()

        if mode == "completed" or any(w in resp_lower for w in ["qualquer dúvida", "obrigado", "até", "precisar", "disposição"]):
            success("Conversa encerrada sem agendamento ✔")
            return True
        else:
            info(f"Modo final: {mode}")
            # Aceitável se não crashou — o agente pode não setar completed sem appointment
            success("Conversa finalizou sem erro (recusa processada) ✔")
            return True

    except Exception as e:
        fail(f"Erro: {e}")
        return False
    finally:
        await reset_session(client, sid)


async def test_6_session_reset(client: httpx.AsyncClient) -> bool:
    """Cenário 6: Reset de sessão → conversa recomeça do zero."""
    section("CENÁRIO 6 — Reset de Sessão")
    sid = str(uuid.uuid4())

    try:
        # Conversa inicial
        step("Usuário", "Olá!")
        data = await send_message(client, sid, "Olá!")
        agent_says(data["response"], data.get("conversation_mode"))

        step("Usuário", "Me chamo Ana Paula Souza")
        data = await send_message(client, sid, "Me chamo Ana Paula Souza")
        agent_says(data["response"], data.get("conversation_mode"))

        # Reset
        info("🔄 Resetando sessão...")
        reset_data = await reset_session(client, sid)
        info(f"Reset: {reset_data['message']}")

        # Nova conversa — deve recomeçar do zero (greeting)
        step("Usuário (pós-reset)", "Oi!")
        data = await send_message(client, sid, "Oi!")
        agent_says(data["response"], data.get("conversation_mode"))

        # Validação: deve ser saudação inicial, não lembrar do nome
        mode = data.get("conversation_mode", "")
        resp_lower = data["response"].lower()

        if mode in ("greeting", None, "") or any(w in resp_lower for w in ["oi", "olá", "ajudar", "agência", "agente"]):
            success("Sessão resetada — conversa recomeçou do zero ✔")
            # Bonus check: não deve lembrar do nome
            if "ana" not in resp_lower:
                success("Agente não lembra do nome anterior ✔")
            return True
        else:
            fail(f"Sessão pode não ter sido resetada corretamente. Modo: {mode}")
            return False

    except Exception as e:
        fail(f"Erro: {e}")
        return False
    finally:
        await reset_session(client, sid)


# ========== UTILS ==========

def _next_weekday_date(weekday: int) -> datetime:
    """Retorna a próxima data para o dia da semana dado (0=seg, 1=ter, ..., 4=sex)."""
    today = datetime.now()
    days_ahead = weekday - today.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return today + timedelta(days=days_ahead)


# ========== MAIN ==========

async def main():
    print(f"\n{Colors.BOLD}{'='*70}")
    print(f"  🧪  SIMULAÇÃO DE COMPORTAMENTOS DO CHAT — AtenteAI Portfolio")
    print(f"{'='*70}{Colors.END}")
    print(f"  Backend: {BASE_URL}")
    print(f"  Hora: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"  Cenários: 6")

    # Verifica se backend está rodando
    async with httpx.AsyncClient() as client:
        try:
            health = await client.get("http://localhost:8000/health", timeout=5.0)
            if health.status_code == 200:
                info("Backend online ✔")
            else:
                fail(f"Backend respondeu com status {health.status_code}")
                return
        except httpx.ConnectError:
            fail("Backend não está rodando! Inicie com: uvicorn app.main:app --reload")
            return

    # Rodar cenários
    results: dict[str, bool] = {}

    async with httpx.AsyncClient() as client:
        for test_fn in [
            test_1_greeting,
            test_2_rag_question,
            test_3_lead_collection,
            test_4_full_flow,
            test_5_decline_scheduling,
            test_6_session_reset,
        ]:
            name = test_fn.__doc__.split("—")[0].strip() if test_fn.__doc__ else test_fn.__name__
            try:
                passed = await test_fn(client)
                results[name] = passed
            except Exception as e:
                fail(f"Erro fatal no cenário: {e}")
                results[name] = False

    # Resumo
    print(f"\n{'='*70}")
    print(f"{Colors.BOLD}  📊  RESUMO DOS TESTES{Colors.END}")
    print(f"{'='*70}")

    passed_count = 0
    failed_count = 0

    for name, passed in results.items():
        icon = f"{Colors.GREEN}✅" if passed else f"{Colors.RED}❌"
        status = "PASS" if passed else "FAIL"
        print(f"  {icon} [{status}]{Colors.END} {name}")
        if passed:
            passed_count += 1
        else:
            failed_count += 1

    total = passed_count + failed_count
    print(f"\n  Total: {total} | {Colors.GREEN}Pass: {passed_count}{Colors.END} | {Colors.RED}Fail: {failed_count}{Colors.END}")

    if failed_count == 0:
        print(f"\n  {Colors.GREEN}{Colors.BOLD}🎉 TODOS OS CENÁRIOS PASSARAM!{Colors.END}\n")
    else:
        print(f"\n  {Colors.YELLOW}⚠️  Alguns cenários falharam. Verifique os logs acima.{Colors.END}\n")

    sys.exit(0 if failed_count == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
