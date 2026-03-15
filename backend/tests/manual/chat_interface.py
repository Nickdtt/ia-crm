"""
Interface de chat simples para testar o agente LangGraph.

Permite conversar com o agente via terminal de forma interativa.
"""

import asyncio
import sys
import uuid
from pathlib import Path
from datetime import datetime

# Adicionar backend ao path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from langchain_core.messages import HumanMessage
from app.agent.graph import marketing_crm_graph


class ChatInterface:
    """Interface de chat interativa para o agente."""
    
    def __init__(self):
        self.session_id = f"chat-{uuid.uuid4().hex[:8]}"
        self.state = {
            "messages": [],
            "session_id": self.session_id
        }
        
    def print_separator(self):
        """Imprime separador visual."""
        print("\n" + "─" * 70 + "\n")
    
    def print_agent_message(self, content: str):
        """Imprime mensagem do agente formatada."""
        print("🤖 AGENTE:", content)
    
    def print_user_message(self, content: str):
        """Imprime mensagem do usuário formatada."""
        print("👤 VOCÊ:", content)
    
    async def send_message(self, user_input: str):
        """Envia mensagem para o agente e processa resposta."""
        
        # Adiciona mensagem do usuário ao estado
        self.state["messages"].append(HumanMessage(content=user_input))
        
        print("\n⏳ Processando...")
        
        try:
            # Invoca o grafo
            result = await marketing_crm_graph.ainvoke(self.state)
            
            # Atualiza estado com resultado
            self.state = result
            
            # Pega última mensagem do agente (AIMessage)
            messages = result.get("messages", [])
            if messages:
                # Filtrar apenas AIMessages
                from langchain_core.messages import AIMessage
                ai_messages = [msg for msg in messages if isinstance(msg, AIMessage)]
                
                if ai_messages:
                    last_msg = ai_messages[-1]
                    content = last_msg.content if hasattr(last_msg, 'content') else str(last_msg)
                    
                    self.print_separator()
                    self.print_agent_message(content)
                    
                    # Debug info
                    current_step = result.get("current_step", "unknown")
                    print(f"\n📍 Step: {current_step}")
                else:
                    print("\n⚠️ Nenhuma resposta do agente encontrada")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Erro: {e}")
            print("\n💡 Dica: Verifique se a API key está configurada no .env")
            import traceback
            traceback.print_exc()
            return False
    
    async def start(self):
        """Inicia o chat interativo."""
        print("=" * 70)
        print("🤖 CHAT COM AGENTE - MARKETING CRM")
        print("=" * 70)
        print(f"\n📱 Session ID: {self.session_id}")
        print("\n💬 Digite suas mensagens abaixo")
        print("⌨️  Comandos especiais:")
        print("   - 'sair' ou 'exit' para encerrar")
        print("   - 'reset' para reiniciar conversa")
        print("   - 'estado' para ver estado atual")
        
        self.print_separator()
        
        while True:
            try:
                # Aguarda input do usuário
                user_input = input("\n👤 VOCÊ: ").strip()
                
                if not user_input:
                    continue
                
                # Comandos especiais
                if user_input.lower() in ['sair', 'exit', 'quit']:
                    print("\n👋 Até logo!")
                    break
                
                if user_input.lower() == 'reset':
                    self.session_id = f"chat-{uuid.uuid4().hex[:8]}"
                    self.state = {
                        "messages": [],
                        "session_id": self.session_id
                    }
                    print(f"\n🔄 Conversa reiniciada! Nova session: {self.session_id}")
                    continue
                
                if user_input.lower() == 'estado':
                    print("\n📊 ESTADO ATUAL:")
                    print(f"   Session ID: {self.state.get('session_id')}")
                    print(f"   Mensagens: {len(self.state.get('messages', []))}")
                    print(f"   Step: {self.state.get('current_step', 'N/A')}")
                    print(f"\n   🔄 MODO (Híbrido):")
                    mode = self.state.get('conversation_mode', 'N/A')
                    print(f"      conversation_mode: {mode}")
                    print(f"\n   🎯 Fluxo:")
                    print(f"      Apresentação feita: {self.state.get('presentation_done', False)}")
                    print(f"      Intenção capturada: {self.state.get('initial_intent_captured', False)}")
                    print(f"      Intenção: {self.state.get('initial_intent', 'N/A')}")
                    print(f"      Permissão pedida: {self.state.get('permission_asked', False)}")
                    print(f"      Qualificação completa: {self.state.get('qualification_complete', False)}")
                    print(f"      Budget qualificado: {self.state.get('budget_qualified', 'N/A')}")
                    print(f"      Perguntou sobre agendamento: {self.state.get('asked_to_schedule', False)}")
                    print(f"      Quer agendar: {self.state.get('wants_to_schedule', 'N/A')}")
                    
                    requested_dt = self.state.get('requested_datetime')
                    if requested_dt:
                        print(f"      Data/hora solicitada: {requested_dt}")
                    
                    slot_available = self.state.get('slot_available')
                    if slot_available is not None:
                        print(f"      Slot disponível: {slot_available}")
                    
                    alternatives = self.state.get('alternative_slots')
                    if alternatives:
                        print(f"      Alternativas oferecidas: {len(alternatives)}")
                    
                    chosen = self.state.get('chosen_slot')
                    if chosen:
                        print(f"      Slot escolhido: {chosen}")
                    
                    client_data = self.state.get('client_data', {})
                    if client_data:
                        print(f"\n   📋 Dados do Cliente:")
                        for key, value in client_data.items():
                            print(f"      - {key}: {value}")
                    continue
                
                # Envia mensagem para o agente
                success = await self.send_message(user_input)
                
                if not success:
                    break
                
            except KeyboardInterrupt:
                print("\n\n👋 Chat interrompido. Até logo!")
                break
            except Exception as e:
                print(f"\n❌ Erro inesperado: {e}")
                break


async def main():
    """Função principal."""
    chat = ChatInterface()
    await chat.start()


if __name__ == "__main__":
    asyncio.run(main())
