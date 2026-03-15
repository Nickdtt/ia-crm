"""
Testes do grafo e do agente LangGraph — Marketing CRM.

Cobre:
- Estrutura do grafo (nós, entry point, rotas)
- Helper get_last_human_message
- Comportamento do entry point (via invocação)
- Fluxos curtos: greeting, saída por keyword, clarification, qualificação

Execução:
  pytest tests/test_agent_graph.py -v
  pytest tests/test_agent_graph.py -v -k "TestGraph or TestGetLast or TestRoute"
  RUN_AGENT_INTEGRATION=1 pytest tests/test_agent_graph.py -v   # inclui fluxos (precisa DB + LLM)
  python tests/test_agent_graph.py
"""

import asyncio
import os
import pytest
from pathlib import Path

# Garante backend no path
_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(_backend))

from langchain_core.messages import HumanMessage, AIMessage


# ========== FIXTURES ==========

@pytest.fixture
def graph():
    """Grafo compilado do agente."""
    from app.agent.graph import marketing_crm_graph
    return marketing_crm_graph


def _new_state(phone: str = "71999999999", **overrides) -> dict:
    """Estado inicial para nova conversa (compatível com state atual)."""
    base = {
        "messages": [],
        "session_id": f"test-{phone}",
        "phone": phone,
        "conversation_mode": None,
        "presentation_done": False,
        "initial_intent_captured": False,
        "permission_asked": False,
        "qualification_complete": False,
        "budget_qualified": False,
        "client_data": {},
        "client_id": None,
        "retry_count": 0,
        "current_question": None,
        "requires_human": False,
    }
    base.update(overrides)
    return base


# ========== TESTES UNITÁRIOS (sem LLM/DB) ==========

class TestGraphStructure:
    """Estrutura do grafo: nós obrigatórios e mapeamento do entry point."""

    def test_graph_compiles(self, graph):
        """Grafo compila sem erros."""
        assert graph is not None

    def test_expected_nodes_exist(self, graph):
        """Todos os nós esperados estão registrados."""
        nodes = set(graph.nodes.keys())
        expected = {
            "greeting", "intent_analyzer", "clarification", "question_answerer",
            "qualification_agent", "budget_filter", "ask_to_schedule",
            "datetime_collector", "slot_checker", "alternative_slots",
            "appointment_creator", "confirmation", "fallback", "thankyou",
            "returning_client_handler",
        }
        missing = expected - nodes
        assert not missing, f"Nós faltando: {missing}"

    def test_has_many_nodes(self, graph):
        """Grafo possui todos os nós principais."""
        nodes = list(graph.nodes.keys())
        assert len(nodes) >= 10
        assert "greeting" in nodes
        assert "intent_analyzer" in nodes
        assert "clarification" in nodes


class TestGetLastHumanMessage:
    """Helper get_last_human_message."""

    def test_returns_last_human_message(self):
        from app.agent.state import get_last_human_message
        state = {
            "messages": [
                HumanMessage(content="Oi"),
                AIMessage(content="Olá! Como posso ajudar?"),
                HumanMessage(content="Quero agendar"),
            ],
        }
        assert get_last_human_message(state) == "Quero agendar"

    def test_ignores_last_ai_message(self):
        """Quando a última mensagem é do agente, retorna a última do humano."""
        from app.agent.state import get_last_human_message
        state = {
            "messages": [
                HumanMessage(content="ok"),
                AIMessage(content="Entendido! Continuando — pode me responder a pergunta anterior?"),
            ],
        }
        assert get_last_human_message(state) == "ok"

    def test_empty_messages_returns_empty_string(self):
        from app.agent.state import get_last_human_message
        assert get_last_human_message({"messages": []}) == ""

    def test_plain_string_in_messages(self):
        """Mensagens podem ser strings (ex.: webhook)."""
        from app.agent.state import get_last_human_message
        state = {"messages": ["Oi", "Quero reunião"]}
        assert get_last_human_message(state) == "Quero reunião"


class TestRouteAfterIntent:
    """Roteamento pós intent_analyzer."""

    def test_requires_human_routes_to_end(self):
        from app.agent.nodes.intent_analyzer import route_after_intent
        state = {"requires_human": True}
        assert route_after_intent(state) == "end"

    def test_wants_meeting_routes_to_meeting(self):
        from app.agent.nodes.intent_analyzer import route_after_intent
        state = {"initial_intent": "wants_meeting", "conversation_mode": None}
        assert route_after_intent(state) == "meeting"

    def test_has_question_routes_to_question(self):
        from app.agent.nodes.intent_analyzer import route_after_intent
        state = {"initial_intent": "has_question"}
        assert route_after_intent(state) == "question"

    def test_unknown_routes_to_clarification(self):
        from app.agent.nodes.intent_analyzer import route_after_intent
        state = {"initial_intent": "unknown", "conversation_mode": None}
        assert route_after_intent(state) == "clarification"

    def test_continue_with_qualification_mode_routes_to_meeting(self):
        from app.agent.nodes.intent_analyzer import route_after_intent
        state = {"interrupt_intent": "continue", "conversation_mode": "qualification"}
        assert route_after_intent(state) == "meeting"


# ========== TESTES DE FLUXO (precisam de LLM; opcionalmente DB) ==========

# Testes de fluxo precisam de DB (greeting) e LLM. Sem DB/LLM, rode só unitários.
RUN_INTEGRATION = os.environ.get("RUN_AGENT_INTEGRATION", "0") == "1"


@pytest.mark.asyncio
@pytest.mark.skipif(not RUN_INTEGRATION, reason="RUN_AGENT_INTEGRATION=0")
class TestFlowGreeting:
    """Primeira interação → greeting."""

    async def test_first_message_goes_to_greeting(self, graph):
        """Mensagem inicial deve passar pelo greeting e retornar apresentação."""
        state = _new_state(phone="71900000001")
        state["messages"].append(HumanMessage(content="Oi"))
        result = await graph.ainvoke(state)
        assert result.get("presentation_done") is True
        assert result.get("current_step") == "greeting"
        messages = result.get("messages", [])
        assert any(
            "agente" in (m.content if hasattr(m, "content") else str(m)).lower()
            for m in messages
        ), "Resposta deve conter apresentação do agente"


@pytest.mark.asyncio
@pytest.mark.skipif(not RUN_INTEGRATION, reason="RUN_AGENT_INTEGRATION=0")
class TestFlowExitKeyword:
    """Saída por keyword (sem LLM para intent)."""

    async def test_exit_keyword_ends_conversation(self, graph):
        """Após greeting, 'não quero mais' deve encerrar (completed)."""
        state = _new_state(phone="71900000002")
        state["messages"].append(HumanMessage(content="Oi"))
        state = await graph.ainvoke(state)
        state["messages"].append(HumanMessage(content="não quero mais"))
        result = await graph.ainvoke(state)
        assert result.get("conversation_mode") == "completed"
        messages = result.get("messages", [])
        last_content = messages[-1].content if messages and hasattr(messages[-1], "content") else ""
        assert "até mais" in last_content.lower() or "sem pressão" in last_content.lower()


@pytest.mark.asyncio
@pytest.mark.skipif(not RUN_INTEGRATION, reason="RUN_AGENT_INTEGRATION=0")
class TestFlowClarification:
    """Intenção não identificada → clarification (menu)."""

    async def test_unclear_gets_clarification_menu(self, graph):
        """Mensagem incompreensível após greeting deve levar a clarification."""
        state = _new_state(phone="71900000003")
        state["messages"].append(HumanMessage(content="Oi"))
        state = await graph.ainvoke(state)
        state["messages"].append(HumanMessage(content="xyz kkk ???"))
        result = await graph.ainvoke(state)
        # Pode ir para clarification ou intent_analyzer pode classificar
        messages = result.get("messages", [])
        last_content = messages[-1].content if messages and hasattr(messages[-1], "content") else ""
        # Esperamos menu (1/2/3) ou resposta de clarificação
        has_menu = "1" in last_content and ("2" in last_content or "agendar" in last_content.lower())
        has_clarification = "não consegui entender" in last_content.lower() or "como posso te ajudar" in last_content.lower()
        assert has_menu or has_clarification or result.get("current_step") == "clarification", (
            f"Esperado menu ou clarification, step={result.get('current_step')}, last={last_content[:120]}"
        )


@pytest.mark.asyncio
@pytest.mark.skipif(not RUN_INTEGRATION, reason="RUN_AGENT_INTEGRATION=0")
class TestFlowQualificationStart:
    """Greeting → resposta positiva → qualificação."""

    async def test_positive_response_after_greeting_goes_to_qualification(self, graph):
        """'Quero agendar' após greeting deve entrar em qualificação."""
        state = _new_state(phone="71900000004")
        state["messages"].append(HumanMessage(content="Oi"))
        state = await graph.ainvoke(state)
        state["messages"].append(HumanMessage(content="Quero marcar uma reunião"))
        result = await graph.ainvoke(state)
        assert result.get("conversation_mode") == "qualification"
        messages = result.get("messages", [])
        last_content = messages[-1].content if messages and hasattr(messages[-1], "content") else ""
        assert "nome" in last_content.lower() or "qual" in last_content.lower(), (
            f"Esperado pergunta de qualificação, obteve: {last_content[:150]}"
        )


# ========== RELATÓRIO (execução via python tests/test_agent_graph.py) ==========

def _run_and_report():
    """Executa testes e imprime relatório legível."""
    import sys
    pytest_args = [
        __file__,
        "-v",
        "--tb=short",
    ]
    code = pytest.main(pytest_args)
    # Mensagem resumida
    if code == 0:
        print("\n📋 Resumo: testes unitários do grafo e do agente passaram.")
        if not RUN_INTEGRATION:
            print("   (Fluxos de integração skipped — use RUN_AGENT_INTEGRATION=1 com DB+LLM para rodar.)")
    sys.exit(code)


if __name__ == "__main__":
    _run_and_report()
