"""
agent.py

Agente PydanticAI para qualificação de leads e agendamento de consultorias
via WhatsApp. Substitui a arquitetura LangGraph anterior.

Arquitetura:
- Um único Agent com 5 ferramentas
- O LLM decide o fluxo naturalmente a partir do histórico de mensagens
- Estado mínimo: phone + client_id + appointment_id
"""

import re
from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from uuid import UUID
from zoneinfo import ZoneInfo

from pydantic import BaseModel
from pydantic_ai import Agent, RunContext

from app.agent.deps import ConversationDeps
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.appointment import Appointment, AppointmentStatus
from app.schemas.appointmentSchema import AppointmentCreate
from app.schemas.clientSchema import ClientCreate, ClientSegment
from app.services.appointmentService import (
    cancel_appointment,
    create_appointment,
    get_available_slots,
)
from app.services.clientService import create_client, get_client_by_phone
from sqlalchemy import select


BRAZIL_TZ = ZoneInfo("America/Sao_Paulo")

# ── Mapeamento segmento texto livre → enum ────────────────────────────────────
SEGMENT_MAPPING: dict[str, str] = {
    "clinica_medica": "clinica_medica",
    "clinica medica": "clinica_medica",
    "medica": "clinica_medica",
    "medico": "clinica_medica",
    "consultorio medico": "clinica_medica",
    "saude": "clinica_medica",
    "clinica_odontologica": "clinica_odontologica",
    "clinica odontologica": "clinica_odontologica",
    "odontologia": "clinica_odontologica",
    "odontologica": "clinica_odontologica",
    "odonto": "clinica_odontologica",
    "consultorio odontologico": "clinica_odontologica",
    "clinica_estetica": "clinica_estetica",
    "clinica estetica": "clinica_estetica",
    "estetica": "clinica_estetica",
    "beleza": "clinica_estetica",
    "laboratorio": "laboratorio",
    "lab": "laboratorio",
    "hospital": "hospital",
    "medico_autonomo": "medico_autonomo",
    "medico autonomo": "medico_autonomo",
    "dentista_autonomo": "dentista_autonomo",
    "dentista autonomo": "dentista_autonomo",
    "dentista": "dentista_autonomo",
    "psicologo": "psicologo",
    "psicologia": "psicologo",
    "terapia": "psicologo",
    "terapeuta": "psicologo",
    "fisioterapeuta": "fisioterapeuta",
    "fisioterapia": "fisioterapeuta",
    "nutricionista": "nutricionista",
    "nutricao": "nutricionista",
    "nutrição": "nutricionista",
    "farmacia": "farmacia",
    "drogaria": "farmacia",
    "ecommerce_saude": "ecommerce_saude",
    "ecommerce saude": "ecommerce_saude",
    "ecommerce": "ecommerce_saude",
    "e-commerce": "ecommerce_saude",
    "loja online": "ecommerce_saude",
    "equipamentos_medicos": "equipamentos_medicos",
    "equipamentos medicos": "equipamentos_medicos",
    "equipamentos": "equipamentos_medicos",
    "plano_saude": "plano_saude",
    "plano de saude": "plano_saude",
    "convenio": "plano_saude",
}


def _map_segment(raw: str) -> str:
    lower = raw.lower().strip()
    if lower in SEGMENT_MAPPING:
        return SEGMENT_MAPPING[lower]
    for key, value in SEGMENT_MAPPING.items():
        if key in lower or lower in key:
            return value
    return "outro"


def _parse_budget_to_float(budget_raw: str) -> float:
    budget_str = str(budget_raw).upper().strip()
    for suffix in ("REAIS", "REAL", "POR MÊS", "POR MES", "MÊS", "MES", "/MÊS", "/MES", "MENSAL"):
        budget_str = budget_str.replace(suffix, " ")
    # "conto" is Brazilian slang for "mil reais" (e.g. "5 conto" = R$5.000)
    if "MIL" in budget_str or "CONTO" in budget_str:
        mil_match = re.search(r"(\d+)", budget_str)
        return float(mil_match.group(1)) * 1000 if mil_match else 0.0
    num_match = re.search(r"[\d.,]+", budget_str)
    if not num_match:
        return 0.0
    budget_clean = num_match.group(0)
    if "." in budget_clean and "," in budget_clean:
        budget_clean = budget_clean.replace(".", "").replace(",", ".")
    elif "," in budget_clean:
        budget_clean = budget_clean.replace(",", ".")
    elif budget_clean.count(".") == 1 and len(budget_clean.split(".")[-1]) == 3:
        budget_clean = budget_clean.replace(".", "")
    try:
        return float(budget_clean) if budget_clean else 0.0
    except ValueError:
        return 0.0


# ── System Prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Você é o agente virtual da "Isso não é uma agência", agência de marketing digital especializada no setor de saúde.

## SUA MISSÃO
Qualificar leads e agendar consultorias de 30 minutos via Google Meet para a equipe comercial.

## REGRA ABSOLUTA — PRIMEIRA MENSAGEM
**SEMPRE** chame `buscar_cliente` como sua PRIMEIRA AÇÃO antes de qualquer resposta, independentemente do que o cliente escreveu. Não responda nada antes de executar `buscar_cliente`.
- Se existir: cumprimente pelo nome, verifique se tem agendamento ativo (via `listar_agendamentos_cliente`) e responda conforme o contexto (agendamento, cancelamento, dúvida etc).
- Se não existir: apresente-se e inicie qualificação.

## FLUXO ESPERADO
2. **Qualificação** (para novos leads ou leads sem agendamento): colete os dados abaixo, **uma pergunta por vez**:
   - Nome (sobrenome é opcional — aceite nome único, apelido ou nome de guerra)
   - Email (opcional — se recusar, aceite e siga)
   - Nome da empresa/negócio (se autônomo, aceite sem empresa)
   - Segmento de atuação na saúde (ex: clínica médica, odontológica, psicologia, fisioterapia, estética...)
   - Principal desafio de marketing hoje
   - Orçamento mensal disponível para marketing digital
3. **Filtro de orçamento**: ao coletar o orçamento, passe o valor EXATAMENTE como o cliente disse para `salvar_cliente` — nunca avalie o orçamento por conta própria antes de chamar a ferramenta. A ferramenta faz a verificação internamente. Atenção: no Brasil, "conto" é gíria para "mil reais" ("5 conto" = R$5.000), "pau" também pode significar mil. Passe sempre o texto bruto.
   - Se `salvar_cliente` retornar sucesso: ofereça agendamento.
   - Se o orçamento for insuficiente (< R$3.000): agradeça e encerre.
4. **Agendamento**:
   - Pergunte qual data e horário prefere.
   - Use `verificar_disponibilidade` para confirmar disponibilidade.
   - Se disponível: chame `criar_agendamento` IMEDIATAMENTE. **NUNCA** diga "Gostaria de agendar?", "Confirma?", "Posso agendar?", "Esse horário serve?" — simplesmente execute a ferramenta e informe a confirmação ao usuário.
   - Se indisponível: apresente os slots alternativos retornados pela ferramenta numerados (1. 09h, 2. 10h...) e aguarde o usuário escolher. Quando escolher, chame `criar_agendamento` com o slot escolhido sem pedir confirmação adicional.
5. **Confirmação**: após criar o agendamento, envie confirmação com data, hora e instruções.

## REGRAS OBRIGATÓRIAS
- **Uma pergunta por vez** — nunca faça duas perguntas na mesma mensagem.
- Seja objetivo e cordial. Máximo 2-3 linhas por resposta.
- **Nunca negocie preços** — orçamento mínimo R$ 3.000 é fixo, sem exceções.
- **Nunca prometa** prazos, resultados ou serviços fora da lista: sites, redes sociais, SEO, tráfego pago, consultoria estratégica.
- **Não agende** fora do horário comercial (seg-sex conforme agenda disponível).
- **Não crie duplicatas** — se o cliente já tem agendamento ativo, pergunte se quer remarcar.
- **Cancelamento**: quando o cliente pedir cancelamento, confirme ("Tem certeza que deseja cancelar?") e só então chame `cancelar_agendamento`.
- **Apenas setor de saúde**: atendemos somente empresas e profissionais que atuam na área da saúde (clínicas, consultórios, laboratórios, farmácias, planos de saúde, etc). Se o negócio não for da área da saúde (ex: padaria, restaurante, advocacia, varejo, tecnologia), encerre gentilmente informando que a agência é especializada exclusivamente em marketing para saúde.
- Se o cliente for claramente um paciente buscando atendimento médico (não um negócio), encerre gentilmente explicando que atendem empresas e profissionais de saúde.
- Se o cliente quiser falar com humano, agradeça e diga que a equipe entrará em contato.

## DATA/HORA ATUAL
Hoje é {today}. Timezone: America/Sao_Paulo.
"""

# ── Schemas para tools ────────────────────────────────────────────────────────
class ClienteData(BaseModel):
    full_name: str
    email: Optional[str] = None
    company_name: Optional[str] = None
    segment: str
    main_marketing_problem: str
    monthly_budget: str


# ── Agente ────────────────────────────────────────────────────────────────────
_model_string = f"{settings.DEFAULT_LLM_PROVIDER}:{settings.DEFAULT_MODEL}"

crm_agent = Agent(
    _model_string,
    deps_type=ConversationDeps,
    system_prompt=SYSTEM_PROMPT,
    defer_model_check=True,
)


@crm_agent.system_prompt
async def inject_today(ctx: RunContext[ConversationDeps]) -> str:
    today = datetime.now(BRAZIL_TZ).strftime("%d/%m/%Y (%A)")
    return f"Hoje é {today}. Timezone: America/Sao_Paulo."


# ── Tools ─────────────────────────────────────────────────────────────────────

@crm_agent.tool
async def buscar_cliente(ctx: RunContext[ConversationDeps]) -> dict:
    """
    Busca o cliente no banco pelo número de telefone.
    Retorna os dados do cliente e lista de agendamentos ativos, ou indica que é cliente novo.
    Sempre chame esta ferramenta na PRIMEIRA mensagem de uma conversa.
    """
    async with AsyncSessionLocal() as db:
        client = await get_client_by_phone(db, ctx.deps.phone)
        if not client:
            return {"encontrado": False}

        ctx.deps.client_id = client.id

        return {
            "encontrado": True,
            "client_id": str(client.id),
            "nome": f"{client.first_name} {client.last_name}",
            "email": client.email,
            "empresa": client.company_name,
            "segmento": client.segment.value if client.segment else None,
            "orcamento": float(client.monthly_budget) if client.monthly_budget else None,
            "problema": client.main_marketing_problem,
        }


@crm_agent.tool
async def listar_agendamentos_cliente(ctx: RunContext[ConversationDeps]) -> dict:
    """
    Lista agendamentos ativos (PENDING ou CONFIRMED) do cliente.
    Use para verificar se cliente retornando já tem reunião marcada.
    """
    if not ctx.deps.client_id:
        return {"agendamentos": [], "mensagem": "Cliente não encontrado no banco ainda."}

    now = datetime.now(BRAZIL_TZ)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Appointment).where(
                Appointment.client_id == ctx.deps.client_id,
                Appointment.status.in_([AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED]),
            ).order_by(Appointment.scheduled_at.asc())
        )
        appointments = result.scalars().all()

    ativos = []
    for apt in appointments:
        apt_time = apt.scheduled_at
        if apt_time.tzinfo is None:
            apt_time = apt_time.replace(tzinfo=BRAZIL_TZ)
        else:
            apt_time = apt_time.astimezone(BRAZIL_TZ)

        if apt_time >= now:
            ativos.append({
                "id": str(apt.id),
                "data_hora": apt_time.strftime("%d/%m/%Y às %Hh%M"),
                "status": apt.status.value,
            })
        else:
            # Marca expirados como NO_SHOW silenciosamente
            async with AsyncSessionLocal() as db2:
                apt_obj = await db2.get(Appointment, apt.id)
                if apt_obj:
                    apt_obj.status = AppointmentStatus.NO_SHOW
                    await db2.commit()

    ctx.deps.appointment_id = UUID(ativos[0]["id"]) if ativos else None
    return {"agendamentos": ativos}


@crm_agent.tool
async def cancelar_agendamento(ctx: RunContext[ConversationDeps]) -> dict:
    """
    Cancela o agendamento ativo do cliente.
    Use apenas quando o cliente confirmar explicitamente que quer cancelar.
    Sempre pergunte se tem certeza antes de chamar esta ferramenta.
    """
    if not ctx.deps.client_id:
        return {"sucesso": False, "erro": "Cliente não encontrado."}

    if not ctx.deps.appointment_id:
        # Tentar encontrar appointment ativo diretamente
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Appointment).where(
                    Appointment.client_id == ctx.deps.client_id,
                    Appointment.status.in_([AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED]),
                ).order_by(Appointment.scheduled_at.asc())
            )
            apt = result.scalars().first()
            if not apt:
                return {"sucesso": False, "erro": "Nenhum agendamento ativo encontrado."}
            ctx.deps.appointment_id = apt.id

    async with AsyncSessionLocal() as db:
        apt_obj = await db.get(Appointment, ctx.deps.appointment_id)
        if not apt_obj:
            return {"sucesso": False, "erro": "Agendamento não encontrado."}
        if apt_obj.status not in (AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED):
            return {"sucesso": False, "erro": "Agendamento já está cancelado ou finalizado."}

        await cancel_appointment(
            appointment_id=ctx.deps.appointment_id,
            reason="Cancelado pelo cliente via WhatsApp",
            db=db,
        )
        ctx.deps.appointment_id = None

    return {"sucesso": True, "mensagem": "Agendamento cancelado com sucesso."}


@crm_agent.tool
async def verificar_disponibilidade(ctx: RunContext[ConversationDeps], data_str: str) -> dict:
    """
    Verifica slots disponíveis para uma data específica.
    Parâmetro data_str: formato 'YYYY-MM-DD' (ex: '2026-03-20').
    Retorna lista de horários livres no formato 'HH:MM', ou lista vazia se sem disponibilidade.
    """
    try:
        target_date = date.fromisoformat(data_str)
    except ValueError:
        return {"erro": f"Formato de data inválido: '{data_str}'. Use YYYY-MM-DD."}

    async with AsyncSessionLocal() as db:
        slots = await get_available_slots(target_date, db)

    if not slots:
        return {
            "data": data_str,
            "slots_disponiveis": [],
            "mensagem": "Sem disponibilidade nesta data. Tente outra data.",
        }

    return {
        "data": data_str,
        "dia_semana": target_date.strftime("%A"),
        "slots_disponiveis": slots,
    }


@crm_agent.tool
async def salvar_cliente(ctx: RunContext[ConversationDeps], dados: ClienteData) -> dict:
    """
    Salva um novo cliente no banco após qualificação completa.
    Chame sempre que todos os dados estiverem coletados — a ferramenta verifica o orçamento internamente.
    Se o orçamento for < R$3.000/mês, retorna orcamento_insuficiente=True e o agente deve encerrar educadamente.
    """
    budget_value = _parse_budget_to_float(dados.monthly_budget)

    if budget_value < 3000.0:
        return {
            "sucesso": False,
            "orcamento_insuficiente": True,
            "orcamento_interpretado": budget_value,
            "mensagem": f"Orçamento R${budget_value:,.0f}/mês está abaixo do mínimo de R$3.000/mês.",
        }

    segment_value = _map_segment(dados.segment)

    name_parts = dados.full_name.strip().split()
    first_name = name_parts[0] if name_parts else ""
    # last_name é obrigatório no schema (min 2 chars) — se não tiver, repete o primeiro nome
    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else first_name

    # Autônomos sem empresa: usar nome como referência
    company_name = dados.company_name
    if not company_name and segment_value in (
        "medico_autonomo", "dentista_autonomo", "psicologo", "fisioterapeuta", "nutricionista"
    ):
        company_name = f"Consultório {first_name}"

    try:
        async with AsyncSessionLocal() as db:
            # Verificar se telefone já existe (prevenção de duplicata)
            existing = await get_client_by_phone(db, ctx.deps.phone)
            if existing:
                ctx.deps.client_id = existing.id
                return {
                    "sucesso": True,
                    "client_id": str(existing.id),
                    "mensagem": "Cliente já existia no banco — ID recuperado.",
                }

            client_create = ClientCreate(
                first_name=first_name,
                last_name=last_name,
                phone=ctx.deps.phone,
                email=dados.email or None,
                company_name=company_name or None,
                segment=segment_value,
                monthly_budget=Decimal(str(budget_value)),
                main_marketing_problem=dados.main_marketing_problem,
            )
            client = await create_client(client_create, db)
            ctx.deps.client_id = client.id

        return {"sucesso": True, "client_id": str(client.id)}

    except Exception as e:
        return {"sucesso": False, "erro": str(e)}


@crm_agent.tool
async def criar_agendamento(ctx: RunContext[ConversationDeps], data_hora_iso: str) -> dict:
    """
    Cria um agendamento para o cliente.
    Parâmetro data_hora_iso: formato ISO 'YYYY-MM-DDTHH:MM' (ex: '2026-03-20T14:00').
    Se o cliente já tiver agendamento ativo, cancela o anterior (remarcação automática).
    """
    if not ctx.deps.client_id:
        return {"sucesso": False, "erro": "Cliente não encontrado. Salve o cliente antes de agendar."}

    try:
        scheduled_at = datetime.fromisoformat(data_hora_iso).replace(tzinfo=BRAZIL_TZ)
    except ValueError:
        return {"sucesso": False, "erro": f"Formato inválido: '{data_hora_iso}'. Use YYYY-MM-DDTHH:MM."}

    now = datetime.now(BRAZIL_TZ)
    if scheduled_at <= now:
        return {"sucesso": False, "erro": "Não é possível agendar no passado. Escolha uma data futura."}

    is_reschedule = False

    async with AsyncSessionLocal() as db:
        # Cancelar agendamentos ativos anteriores (remarcação)
        result = await db.execute(
            select(Appointment).where(
                Appointment.client_id == ctx.deps.client_id,
                Appointment.status.in_([AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED]),
            )
        )
        existing = result.scalars().all()
        if existing:
            is_reschedule = True
            for apt in existing:
                await cancel_appointment(
                    appointment_id=apt.id,
                    reason="Remarcado pelo cliente via WhatsApp",
                    db=db,
                )

        appointment_data = AppointmentCreate(
            client_id=ctx.deps.client_id,
            scheduled_at=scheduled_at,
            duration_minutes=30,
            meeting_type="CONSULTORIA_INICIAL",
            notes="Remarcação via WhatsApp" if is_reschedule else "Agendamento via WhatsApp",
        )
        appointment = await create_appointment(appointment_data, db)
        ctx.deps.appointment_id = appointment.id

    dia_semana = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"][scheduled_at.weekday()]
    data_fmt = scheduled_at.strftime("%d/%m/%Y às %Hh%M" if scheduled_at.minute > 0 else "%d/%m/%Y às %Hh")

    return {
        "sucesso": True,
        "appointment_id": str(ctx.deps.appointment_id),
        "remarcacao": is_reschedule,
        "data_hora_formatada": f"{dia_semana}, {data_fmt}",
        "duracao": "30 minutos",
        "formato": "Google Meet (link enviado por email)",
    }
