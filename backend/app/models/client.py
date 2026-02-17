import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, Text, DateTime, Numeric, Enum as SQLEnum, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.appointment import Appointment
    from app.models.conversation import Conversation


class ClientSegment(str, enum.Enum):
    """Segmentos de mercado focados em saúde"""
    # Prestadores de Serviços de Saúde
    CLINICA_MEDICA = "clinica_medica"
    CLINICA_ODONTOLOGICA = "clinica_odontologica"
    CLINICA_ESTETICA = "clinica_estetica"
    LABORATORIO = "laboratorio"
    HOSPITAL = "hospital"
    
    # Profissionais Autônomos
    MEDICO_AUTONOMO = "medico_autonomo"
    DENTISTA_AUTONOMO = "dentista_autonomo"
    PSICOLOGO = "psicologo"
    FISIOTERAPEUTA = "fisioterapeuta"
    NUTRICIONISTA = "nutricionista"
    
    # Produtos e E-commerce
    FARMACIA = "farmacia"
    ECOMMERCE_SAUDE = "ecommerce_saude"
    EQUIPAMENTOS_MEDICOS = "equipamentos_medicos"
    
    # Outros
    PLANO_SAUDE = "plano_saude"
    OUTRO = "outro"


class Client(Base):
    """
    Cliente que agenda reuniões de marketing.
    
    Captura informações essenciais para qualificação e atendimento:
    - Dados de contato (WhatsApp, email)
    - Informações comerciais (empresa, segmento, orçamento)
    - Contexto de necessidade (problema principal de marketing)
    """
    __tablename__ = "clients"
    
    # Identificação
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    
    # Dados Pessoais
    first_name: Mapped[str] = mapped_column(
        String(100), 
        comment="Primeiro nome do cliente"
    )
    last_name: Mapped[str] = mapped_column(
        String(100), 
        comment="Sobrenome do cliente"
    )
    
    # Contato (WhatsApp é obrigatório e único)
    phone: Mapped[str] = mapped_column(
        String(20), 
        unique=True, 
        index=True,
        comment="Telefone/WhatsApp (identificador único)"
    )
    email: Mapped[str | None] = mapped_column(
        String(255), 
        nullable=True,
        comment="Email de contato"
    )
    
    # Informações Comerciais
    company_name: Mapped[str | None] = mapped_column(
        String(255), 
        nullable=True,
        comment="Nome da empresa (opcional para autônomos PF)"
    )
    segment: Mapped[ClientSegment | None] = mapped_column(
        SQLEnum(ClientSegment),
        nullable=True,
        default=ClientSegment.OUTRO,
        comment="Segmento de atuação (foco em saúde). Nullable para leads via chat."
    )
    monthly_budget: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Orçamento mensal disponível para marketing (R$). Nullable para leads via chat."
    )
    
    # Contexto de Necessidade
    main_marketing_problem: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Principal problema/desafio de marketing atual. Nullable para leads via chat."
    )
    
    # Observações Gerais
    notes: Mapped[str | None] = mapped_column(
        Text, 
        nullable=True,
        comment="Anotações adicionais sobre o cliente"
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now()
    )
    
    # Relationships
    appointments: Mapped[list["Appointment"]] = relationship(
        back_populates="client",
        cascade="all, delete-orphan"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="client",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Client {self.first_name} {self.last_name} ({self.segment.value})>"
    
    @property
    def full_name(self) -> str:
        """Retorna nome completo formatado"""
        return f"{self.first_name} {self.last_name}"
