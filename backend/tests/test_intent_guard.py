"""
Teste local do Intent Guard — simula conversa completa no terminal.

Como rodar:
  cd backend
  source venv/bin/activate
  python tests/test_intent_guard.py

Cenários testados:
  1. Fluxo normal (sem interrupção)    → guard deve retornar "continue" em todas as etapas
  2. Cliente pede para encerrar        → guard detecta "wants_exit"
  3. Cliente faz pergunta no meio      → guard detecta "wants_question"
  4. Cliente quer mudar horário        → guard detecta "wants_reschedule"
  5. Mensagem off-topic (emoji/saudação) → guard detecta "off_topic"
  6. Paciente fora de escopo           → guard detecta "out_of_scope"
"""

import asyncio
import sys
import os
import importlib.util

# Carrega .env ANTES de qualquer import do app (config.py valida as vars no import)
try:
    from dotenv import load_dotenv
    _env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    load_dotenv(os.path.abspath(_env_path))
    print(f"📦 .env carregado de: {os.path.abspath(_env_path)}")
except Exception as e:
    print(f"⚠️  Não foi possível carregar .env: {e}")

# Permite importar módulos do backend
_backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _backend_root)

# Importa intent_guard diretamente pelo path (evita __init__.py que puxa database.py)
_guard_path = os.path.join(_backend_root, "app", "agent", "nodes", "intent_guard.py")
_spec = importlib.util.spec_from_file_location("intent_guard", _guard_path)
_mod  = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
intent_guard_node = _mod.intent_guard_node

from langchain_core.messages import HumanMessage, AIMessage


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_state(user_msg: str, mode: str = "qualification", history: list = None) -> dict:
    """Monta estado mínimo para testar o guard."""
    messages = history or []
    messages.append(HumanMessage(content=user_msg))
    return {
        "messages": messages,
        "conversation_mode": mode,
        "client_data": {"full_name": "Carlos Souza"},
        "interrupt_intent": None,
        "current_step": None,
    }


def color(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m"

GREEN  = "32"
RED    = "31"
YELLOW = "33"
CYAN   = "36"
BOLD   = "1"


async def run_single(label: str, user_msg: str, mode: str, expected: str, history: list = None):
    state = make_state(user_msg, mode, history)
    result = await intent_guard_node(state)
    intent = result.get("interrupt_intent", "???")

    ok = intent == expected
    status = color("✅ PASS", GREEN) if ok else color("❌ FAIL", RED)
    intent_str = color(intent, CYAN)
    expected_str = color(expected, YELLOW)

    print(f"{status}  [{label}]")
    print(f"       msg='{user_msg[:70]}'")
    print(f"       modo={mode}  resultado={intent_str}  esperado={expected_str}")
    if result.get("messages"):
        ai_msg = result["messages"][0].content[:100].replace("\n", " ")
        print(f"       resposta='{ai_msg}...'")
    print()
    return ok


async def main():
    print()
    print(color("=" * 65, BOLD))
    print(color("  INTENT GUARD — Testes unitários", BOLD))
    print(color("=" * 65, BOLD))
    print()

    results = []

    # ── Cenário 1: Respostas normais de qualificação ──────────────────────────
    print(color("── Cenário 1: Fluxo normal (deve retornar 'continue') ──", BOLD))

    history_q = [
        AIMessage(content="Qual é o seu nome completo?"),
    ]
    results.append(await run_single(
        "Nome fornecido",
        "Carlos Souza",
        "qualification", "continue", history_q
    ))
    results.append(await run_single(
        "Email fornecido",
        "carlos@clinicasouza.com.br",
        "qualification", "continue"
    ))
    results.append(await run_single(
        "Segmento fornecido",
        "Tenho uma clínica odontológica",
        "qualification", "continue"
    ))
    results.append(await run_single(
        "Budget fornecido",
        "Meu orçamento é R$ 8.000 por mês",
        "qualification", "continue"
    ))
    results.append(await run_single(
        "Confirmação de horário",
        "Pode ser quarta às 10h",
        "scheduling", "continue"
    ))
    results.append(await run_single(
        "Escolha de alternativa",
        "Prefiro a opção 2",
        "scheduling", "continue"
    ))

    # ── Cenário 2: Cliente quer encerrar ──────────────────────────────────────
    print(color("── Cenário 2: wants_exit ──", BOLD))

    results.append(await run_single(
        "Não quero mais (keyword)",
        "Não quero mais, obrigado",
        "qualification", "wants_exit"
    ))
    results.append(await run_single(
        "Sem interesse",
        "Sem interesse no momento",
        "qualification", "wants_exit"
    ))
    results.append(await run_single(
        "Tchau",
        "Tchau, precisando entro em contato",
        "scheduling", "wants_exit"
    ))

    # ── Cenário 3: Pergunta fora de contexto ──────────────────────────────────
    print(color("── Cenário 3: wants_question ──", BOLD))

    history_mid = [
        AIMessage(content="Qual o nome da sua empresa?"),
    ]
    results.append(await run_single(
        "Pergunta sobre serviços no meio da qualificação",
        "Espera, antes de responder — como funciona exatamente o trabalho de vocês?",
        "qualification", "wants_question", history_mid
    ))
    results.append(await run_single(
        "Pergunta sobre preço",
        "Quanto custa o serviço de vocês?",
        "qualification", "wants_question"
    ))

    # ── Cenário 4: Quer mudar horário ─────────────────────────────────────────
    print(color("── Cenário 4: wants_reschedule ──", BOLD))

    history_sched = [
        AIMessage(content="Ótimo! Vamos confirmar: quarta-feira às 10h, certo?"),
    ]
    results.append(await run_single(
        "Quer mudar o horário",
        "Na verdade quero mudar, prefiro sexta-feira",
        "scheduling", "wants_reschedule", history_sched
    ))
    results.append(await run_single(
        "Pediu outro dia",
        "Tem outro horário disponível? Quarta não vai dar pra mim",
        "scheduling", "wants_reschedule", history_sched
    ))

    # ── Cenário 5: Off-topic ──────────────────────────────────────────────────
    print(color("── Cenário 5: off_topic ──", BOLD))

    results.append(await run_single(
        "Emoji solto",
        "👍",
        "qualification", "off_topic"
    ))
    results.append(await run_single(
        "Saudação genérica",
        "Bom dia!",
        "qualification", "off_topic"
    ))

    # ── Cenário 6: Fora de escopo ─────────────────────────────────────────────
    print(color("── Cenário 6: out_of_scope ──", BOLD))

    results.append(await run_single(
        "Paciente pedindo implante",
        "Quero fazer implante dentário",
        "qualification", "out_of_scope"
    ))
    results.append(await run_single(
        "Paciente buscando consulta",
        "Quero marcar uma consulta",
        "qualification", "out_of_scope"
    ))

    # ── Resultado final ───────────────────────────────────────────────────────
    passed = sum(results)
    total  = len(results)
    pct    = int(100 * passed / total) if total else 0

    print(color("=" * 65, BOLD))
    print(color(f"  Resultado: {passed}/{total} passaram ({pct}%)", BOLD))
    print(color("=" * 65, BOLD))
    print()

    if passed < total:
        print(color("⚠️  Alguns testes falharam. Verifique os prompts do guard.", YELLOW))
        sys.exit(1)
    else:
        print(color("🎉 Todos os testes passaram!", GREEN))


if __name__ == "__main__":
    asyncio.run(main())
