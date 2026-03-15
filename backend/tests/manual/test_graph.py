"""
Script de teste para validar o LangGraph Agent do Marketing CRM.

Testa:
1. Importação de todos os módulos
2. Compilação do graph
3. Execução simulada com mensagem de teste
"""

import asyncio
import sys
from pathlib import Path

# Adicionar backend ao path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from langchain_core.messages import HumanMessage
from app.agent.graph import marketing_crm_graph


async def test_graph_compilation():
    """Testa se o graph compila sem erros."""
    print("🧪 Teste 1: Compilação do graph")
    try:
        graph = marketing_crm_graph
        print("✅ Graph compilado com sucesso!")
        print(f"   Nodes: {list(graph.get_graph().nodes.keys())}")
        return True
    except Exception as e:
        print(f"❌ Erro na compilação: {e}")
        return False


async def test_simple_message():
    """Testa execução com mensagem simples."""
    print("\n🧪 Teste 2: Execução com mensagem simples")
    
    initial_state = {
        "messages": [HumanMessage(content="Olá!")],
        "session_id": "test-session-001"
    }
    
    try:
        result = await marketing_crm_graph.ainvoke(initial_state)
        print("✅ Graph executado com sucesso!")
        print(f"   Step final: {result.get('current_step')}")
        print(f"   Mensagens totais: {len(result.get('messages', []))}")
        
        # Mostrar última mensagem do agente
        messages = result.get("messages", [])
        if messages:
            last_msg = messages[-1]
            content = last_msg.content if hasattr(last_msg, 'content') else str(last_msg)
            print(f"   Última resposta: {content[:100]}...")
        
        return True
    except Exception as e:
        print(f"❌ Erro na execução: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Executa todos os testes."""
    print("=" * 60)
    print("TESTE DO LANGGRAPH AGENT - MARKETING CRM")
    print("=" * 60)
    
    # Teste 1: Compilação
    test1_passed = await test_graph_compilation()
    
    if not test1_passed:
        print("\n❌ Falha na compilação. Abortando testes.")
        return
    
    # Teste 2: Execução simples
    test2_passed = await test_simple_message()
    
    # Resumo
    print("\n" + "=" * 60)
    print("RESUMO DOS TESTES")
    print("=" * 60)
    print(f"Compilação: {'✅ PASS' if test1_passed else '❌ FAIL'}")
    print(f"Execução:   {'✅ PASS' if test2_passed else '❌ FAIL'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 Todos os testes passaram!")
    else:
        print("\n⚠️ Alguns testes falharam. Verifique os erros acima.")


if __name__ == "__main__":
    asyncio.run(main())
