from dataclasses import dataclass, field
from uuid import UUID


@dataclass
class ConversationDeps:
    """
    Dependências injetadas no agente PydanticAI por conversa.

    phone:          Número normalizado do cliente (ex: 71987217380)
    client_id:      UUID do Client no banco — preenchido após buscar_cliente ou salvar_cliente
    appointment_id: UUID do Appointment ativo — preenchido após criar_agendamento
    """
    phone: str
    client_id: UUID | None = field(default=None)
    appointment_id: UUID | None = field(default=None)
