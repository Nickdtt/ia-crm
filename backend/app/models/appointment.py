import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, Enum as SQLEnum, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.client import Client


class AppointmentStatus(str, enum.Enum):
    """Status do agendamento de reunião"""
    PENDING = "pending"      # Aguardando confirmação
    CONFIRMED = "confirmed"  # Confirmado pelo cliente
    CANCELLED = "cancelled"  # Cancelado
    COMPLETED = "completed"  # Reunião realizada
    BLOCKED = "blocked"      # Dia/turno bloqueado administrativamente (minúsculo)


class Appointment(Base):
    """
    Agendamento de reunião de marketing.
    
    Representa uma reunião marcada entre a agência e o cliente.
    Criado manualmente pelo admin ou automaticamente pelo agente IA.
    """
    __tablename__ = "appointments"
    
    # Identificação
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    
    # Relacionamento com Cliente
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("clients.id"),
        comment="Cliente que agendou a reunião"
    )
    
    # Detalhes da Reunião
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        comment="Data e hora agendada para a reunião"
    )
    duration_minutes: Mapped[int] = mapped_column(
        Integer, 
        default=60,
        comment="Duração da reunião em minutos (padrão 60)"
    )
    meeting_type: Mapped[str | None] = mapped_column(
        String(50), 
        nullable=True,
        comment="Tipo de reunião (ex: 'Inicial', 'Follow-up')"
    )
    
    # Status e Gerenciamento
    status: Mapped[AppointmentStatus] = mapped_column(
        SQLEnum(AppointmentStatus), 
        default=AppointmentStatus.PENDING,
        comment="Status atual do agendamento"
    )
    notes: Mapped[str | None] = mapped_column(
        Text, 
        nullable=True,
        comment="Observações sobre a reunião"
    )
    
    # Cancelamento
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), 
        nullable=True,
        comment="Data/hora do cancelamento"
    )
    cancellation_reason: Mapped[str | None] = mapped_column(
        Text, 
        nullable=True,
        comment="Motivo do cancelamento"
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
    client: Mapped["Client"] = relationship(
        back_populates="appointments"
    )
    
    def __repr__(self) -> str:
        return f"<Appointment {self.scheduled_at} status={self.status.value}>"
    
    @property
    def is_active(self) -> bool:
        """Verifica se o agendamento está ativo (não cancelado/completado)"""
        return self.status in [AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED]
