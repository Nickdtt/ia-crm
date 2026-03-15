"""
Script de teste automatizado para demonstrar a versão híbrida do agente.

Simula uma conversa completa mostrando:
1. Logs de roteamento (Modo Declarativo vs Fallback)
2. Campo conversation_mode em cada etapa
3. Transições de modo explícitas
"""

import asyncio
import sys
from pathlib import Path

# Adicionar backend ao path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from langchain_core.messages import HumanMessage
from app.agent.graph import marketing_crm_graph


async def test_hybrid_routing():
    """Testa a versão híbrida com uma conversa completa."""
    
    print("=" * 80)
    print("🧪 TESTE DA VERSÃO HÍBRIDA - ROTEAMENTO DECLARATIVO")
    print("=" * 80)
    
    state = {"messages": []}
    
    # Mensagens de teste simulando fluxo completo
    test_messages = [
        "Oi!",
        "Quero marcar uma reunião",
        "João",
        "Silva",
        "71999887766",
        "Clínica odontológica",
        "Atrair novos pacientes",
        "8 mil por mês"
    ]
    
    for i, msg in enumerate(test_messages, 1):
        print(f"\n{'='*80}")
        print(f"📨 MENSAGEM {i}: \"{msg}\"")
        print(f"{'='*80}")
        
        # Adiciona mensagem do usuário
        state["messages"].append(HumanMessage(content=msg))
        
        # Mostra estado ANTES do processamento
        mode_before = state.get("conversation_mode", "None")
        print(f"\n🔵 ESTADO ANTES:")
        print(f"   conversation_mode: {mode_before}")
        
        # Invoca o grafo
        print(f"\n⏳ Processando...")
        result = await marketing_crm_graph.ainvoke(state)
        state = result
        
        # Mostra estado DEPOIS do processamento
        mode_after = state.get("conversation_mode", "None")
        step = state.get("current_step", "unknown")
        
        print(f"\n🟢 ESTADO DEPOIS:")
        print(f"   conversation_mode: {mode_after}")
        print(f"   current_step: {step}")
        
        # Mostra transição de modo
        if mode_before != mode_after:
            print(f"\n   🔄 TRANSIÇÃO: {mode_before} → {mode_after}")
        
        # Pega última mensagem do agente
        from langchain_core.messages import AIMessage
        ai_messages = [msg for msg in state.get("messages", []) if isinstance(msg, AIMessage)]
        if ai_messages:
            last_msg = ai_messages[-1]
            content = last_msg.content if hasattr(last_msg, 'content') else str(last_msg)
            print(f"\n🤖 RESPOSTA:")
            print(f"   {content[:200]}...")  # Primeiros 200 chars
        
        # Pausa curta para visualização
        await asyncio.sleep(0.5)
    
    # Estado final
    print(f"\n{'='*80}")
    print(f"📊 ESTADO FINAL")
    print(f"{'='*80}")
    print(f"\n🎯 Campos Principais:")
    print(f"   conversation_mode: {state.get('conversation_mode')}")
    print(f"   current_step: {state.get('current_step')}")
    print(f"   qualification_complete: {state.get('qualification_complete')}")
    print(f"   budget_qualified: {state.get('budget_qualified')}")
    
    client_data = state.get('client_data', {})
    if client_data:
        print(f"\n📋 Dados do Cliente:")
        for key, value in client_data.items():
            print(f"   - {key}: {value}")
    
    print(f"\n{'='*80}")
    print(f"✅ TESTE CONCLUÍDO!")
    print(f"{'='*80}")
    
    # Análise de roteamento
    print(f"\n📈 ANÁLISE DE ROTEAMENTO:")
    print(f"   - Logs mostram se usou 'Mode=...' (Declarativo) ou '[Fallback]'")
    print(f"   - conversation_mode transicionou ao longo da conversa")
    print(f"   - Próxima mensagem usará roteamento declarativo se modo estiver setado")


if __name__ == "__main__":
    asyncio.run(test_hybrid_routing())
