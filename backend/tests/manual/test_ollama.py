"""
Script de teste para validar LLM Factory com Ollama.

Testa se o Ollama está configurado corretamente e respondendo.
"""

import asyncio
from app.core.llm_factory import get_llm, get_llm_info
from langchain_core.messages import HumanMessage


async def test_ollama():
    """Testa conexão e resposta do Ollama."""
    
    print("="*60)
    print("🧪 TESTE DO LLM FACTORY")
    print("="*60)
    
    # 1. Mostrar configuração atual
    info = get_llm_info()
    print(f"\n📋 Configuração atual:")
    print(f"   Provider: {info['provider']}")
    print(f"   Model: {info.get('model', 'N/A')}")
    print(f"   Temperature: {info['temperature']}")
    if 'base_url' in info:
        print(f"   Base URL: {info['base_url']}")
    
    # 2. Obter instância do LLM
    try:
        print(f"\n🔧 Inicializando LLM...")
        llm = get_llm()
        print(f"✅ LLM inicializado com sucesso!")
        print(f"   Tipo: {type(llm).__name__}")
    except Exception as e:
        print(f"❌ Erro ao inicializar LLM: {e}")
        return
    
    # 3. Teste simples de resposta
    print(f"\n💬 Testando resposta do modelo...")
    print(f"   Pergunta: 'Olá, você está funcionando?'")
    
    try:
        messages = [
            HumanMessage(content="Olá, você está funcionando? Responda apenas 'Sim, estou funcionando!' em português.")
        ]
        
        response = await llm.ainvoke(messages)
        
        print(f"\n✅ Resposta recebida:")
        print(f"   {response.content}")
        
    except Exception as e:
        print(f"\n❌ Erro ao invocar LLM: {e}")
        print(f"\n💡 Dicas:")
        print(f"   - Verifique se o Ollama está rodando: ollama serve")
        print(f"   - Verifique se o modelo está baixado: ollama list")
        print(f"   - Tente baixar o modelo: ollama pull phi3:mini")
        return
    
    # 4. Teste com prompt mais complexo
    print(f"\n🧠 Testando prompt complexo...")
    print(f"   Pergunta: 'Explique em uma frase o que é LangChain'")
    
    try:
        messages = [
            HumanMessage(content="Explique em apenas uma frase curta o que é LangChain.")
        ]
        
        response = await llm.ainvoke(messages)
        
        print(f"\n✅ Resposta recebida:")
        print(f"   {response.content}")
        
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        return
    
    print(f"\n" + "="*60)
    print(f"✅ TODOS OS TESTES PASSARAM!")
    print(f"="*60)
    print(f"\n💡 Para usar no sistema:")
    print(f"   1. Certifique-se que DEFAULT_LLM_PROVIDER=ollama no .env")
    print(f"   2. Inicie o backend: uvicorn app.main:app --reload")
    print(f"   3. O agente usará automaticamente o Ollama local!")
    print(f"\n")


if __name__ == "__main__":
    asyncio.run(test_ollama())
