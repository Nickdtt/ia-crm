"""
whatsappControllers.py

Webhook que recebe mensagens do WhatsApp via Evolution API,
processa com PydanticAI Agent e responde automaticamente.
"""

from fastapi import APIRouter, Request, status
import httpx
import asyncio
import random
from typing import Dict, Any
from collections import defaultdict
from uuid import UUID

from app.agent.agent import crm_agent
from app.agent.deps import ConversationDeps
from app.core.config import settings

router = APIRouter(
    prefix="/webhook",
    tags=["webhook"],
    responses={
        200: {"description": "Webhook recebido com sucesso"},
        400: {"description": "Requisição inválida"}
    }
)

# ========== ARMAZENAMENTO DE ESTADO (temporário em memória) ==========
# TODO: Migrar para Redis para produção
# Estrutura por usuário:
# {
#   "messages": list[ModelMessage],  — histórico PydanticAI serializado
#   "phone": str,
#   "client_id": UUID | None,
#   "appointment_id": UUID | None,
# }
user_states: Dict[str, Dict[str, Any]] = {}

# ========== CONTROLE DE CONCORRÊNCIA ==========
user_locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

# ========== CONFIGURAÇÃO DE FILTROS ==========
NUMEROS_TESTE = [
    "557187217380@s.whatsapp.net"
]
MODO_TESTE = False  # Mudar para False em produção


async def enviar_presence(remote_jid: str, instance: str, status: str, delay_ms: int = 1200):
    """
    Envia status de presença (composing/paused) via Evolution API v2.
    Usado para simular digitação.
    """
    url = f"{settings.EVOLUTION_API_URL}/chat/sendPresence/{instance}"
    data = {
        "number": remote_jid,
        "delay": delay_ms,
        "presence": status
    }
    headers = {"apikey": settings.EVOLUTION_API_KEY}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data, headers=headers)
            if response.status_code not in [200, 201]:
                print(f"⚠️ Erro ao enviar presence: {response.text}")
            else:
                print(f"✅ Presence '{status}' enviado (delay: {delay_ms}ms)")
    except Exception as e:
        print(f"⚠️ Erro ao enviar presence: {e}")


async def simular_digitacao(remote_jid: str, instance: str, resposta: str, payload: Dict[str, Any]):
    """
    Simula digitação natural antes de enviar mensagem.

    Cálculo:
    - Tempo base: 2-4s aleatório
    - Proporcional: +0.5s a cada 10 caracteres
    - Limite: 2-15s
    """
    tempo_base = random.uniform(2.0, 4.0)
    tempo_caracteres = len(resposta) / 10 * 0.5
    tempo_total = max(2.0, min(15.0, tempo_base + tempo_caracteres))
    tempo_ms = int(tempo_total * 1000)

    print(f"⏳ Aguardando {tempo_total:.1f}s antes de responder...")

    await enviar_presence(remote_jid, instance, "composing", delay_ms=tempo_ms)
    await asyncio.sleep(tempo_total)
    await enviar_presence(remote_jid, instance, "paused", delay_ms=0)
    await enviar_resposta_whatsapp(payload, resposta)


async def enviar_resposta_whatsapp(payload: Dict[str, Any], resposta: str):
    """Envia resposta via Evolution API."""
    remote_jid = payload["data"]["key"]["remoteJid"]
    instance = payload.get("instance")

    url = f"{settings.EVOLUTION_API_URL}/message/sendText/{instance}"
    data = {
        "number": remote_jid,
        "text": resposta
    }
    headers = {"apikey": settings.EVOLUTION_API_KEY}

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data, headers=headers)
        if response.status_code not in [200, 201]:
            print(f"❌ Erro ao enviar mensagem: {response.text}")
        else:
            print(f"✅ Mensagem enviada para {remote_jid}")


@router.post("/whatsapp{full_path:path}", status_code=status.HTTP_200_OK)
async def whatsapp_webhook(request: Request, full_path: str):
    """
    Recebe webhooks do Evolution API, processa com PydanticAI Agent
    e responde automaticamente.

    Fluxo:
    1. Filtra apenas mensagens recebidas (fromMe: False, não grupos)
    2. LOCK por usuário — processamento sequencial
    3. Carrega estado em memória (messages + client_id + appointment_id)
    4. Chama crm_agent.run() com histórico
    5. Salva estado atualizado
    6. Simula digitação e envia resposta
    """
    payload = await request.json()

    if payload.get("event") == "messages.upsert":
        data = payload.get("data", {})
        key = data.get("key", {})
        from_me = key.get("fromMe")
        remote_jid = key.get("remoteJid")

        # Ignora mensagens enviadas por nós
        if from_me:
            return {"status": "ok"}

        # Ignora grupos
        if "@g.us" in remote_jid:
            return {"status": "ok"}

        # Modo teste: só processa números da lista
        if MODO_TESTE and remote_jid not in NUMEROS_TESTE:
            return {"status": "ok"}

        async with user_locks[remote_jid]:
            texto = data.get("message", {}).get("conversation")
            if not texto:
                return {"status": "ok"}

            # Normalizar telefone brasileiro: 557187217380 → 71987217380
            phone_number = remote_jid.split("@")[0]
            if phone_number.startswith("55") and len(phone_number) == 12:
                ddd = phone_number[2:4]
                numero = phone_number[4:]
                phone_number = f"{ddd}9{numero}"

            print(f"📩 Mensagem de {phone_number}: {texto}")

            # Carregar estado em memória
            state = user_states.get(remote_jid, {
                "messages": [],
                "phone": phone_number,
                "client_id": None,
                "appointment_id": None,
            })

            # Reconstruir client_id/appointment_id como UUID se existirem
            client_id = state.get("client_id")
            if client_id and not isinstance(client_id, UUID):
                try:
                    client_id = UUID(str(client_id))
                except ValueError:
                    client_id = None

            appointment_id = state.get("appointment_id")
            if appointment_id and not isinstance(appointment_id, UUID):
                try:
                    appointment_id = UUID(str(appointment_id))
                except ValueError:
                    appointment_id = None

            deps = ConversationDeps(
                phone=phone_number,
                client_id=client_id,
                appointment_id=appointment_id,
            )

            try:
                result = await crm_agent.run(
                    texto,
                    message_history=state["messages"],
                    deps=deps,
                )

                resposta = result.output
                print(f"🤖 Agent respondeu: {resposta}")

                # Salvar estado atualizado
                user_states[remote_jid] = {
                    "messages": result.all_messages(),
                    "phone": phone_number,
                    "client_id": deps.client_id,
                    "appointment_id": deps.appointment_id,
                }

                # Simular digitação e enviar
                instance = payload.get("instance")
                await simular_digitacao(remote_jid, instance, resposta, payload)

            except Exception as e:
                print(f"❌ Erro ao processar mensagem: {e}")
                await enviar_resposta_whatsapp(
                    payload,
                    "Desculpe, ocorreu um erro temporário. Tente novamente em instantes."
                )

    return {"status": "ok"}
