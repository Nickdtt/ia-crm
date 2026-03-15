from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timezone
from uuid import UUID
from typing import Optional


class AppointmentCreate(BaseModel):
    """Schema para criar novo agendamento de reunião."""
    
    client_id: UUID = Field(..., description="ID do cliente")
    scheduled_at: datetime = Field(..., description="Data e hora do agendamento")
    duration_minutes: int = Field(
        default=60, 
        ge=15, 
        le=480,
        description="Duração em minutos (padrão: 60min, máx: 8h)"
    )
    meeting_type: Optional[str] = Field(
        None, 
        max_length=100,
        description="Tipo de reunião (ex: 'Diagnóstico inicial', 'Follow-up')"
    )
    notes: Optional[str] = Field(
        None, 
        max_length=500, 
        description="Observações sobre a reunião"
    )
    
    @field_validator('scheduled_at')
    @classmethod
    def validate_future_date(cls, v: datetime) -> datetime:
        """Valida se o agendamento é para data futura."""
        now = datetime.now(timezone.utc)
        # Garante que v também seja timezone-aware
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        if v < now:
            raise ValueError('O agendamento deve ser para uma data futura')
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "client_id": "660e8400-e29b-41d4-a716-446655440001",
                "scheduled_at": "2025-12-25T10:00:00",
                "duration_minutes": 60,
                "meeting_type": "Diagnóstico inicial",
                "notes": "Primeira reunião com o cliente"
            }
        }
    }


class AppointmentUpdate(BaseModel):
    """Schema para atualizar agendamento existente (campos opcionais)."""
    
    scheduled_at: Optional[datetime] = Field(
        None, 
        description="Nova data e hora (opcional)"
    )
    duration_minutes: Optional[int] = Field(
        None,
        ge=15,
        le=480,
        description="Nova duração em minutos (opcional)"
    )
    meeting_type: Optional[str] = Field(
        None,
        max_length=100,
        description="Novo tipo de reunião (opcional)"
    )
    notes: Optional[str] = Field(
        None,
        max_length=500,
        description="Novas observações (opcional)"
    )
    status: Optional[str] = Field(
        None,
        description="Novo status (opcional)"
    )
    cancellation_reason: Optional[str] = Field(
        None,
        max_length=200,
        description="Motivo do cancelamento (opcional)"
    )
    
    @field_validator('scheduled_at')
    @classmethod
    def validate_future_date(cls, v: Optional[datetime]) -> Optional[datetime]:
        """Valida se o novo agendamento é para data futura."""
        if v is not None and v < datetime.now():
            raise ValueError('O agendamento deve ser para uma data futura')
        return v
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "scheduled_at": "2025-12-26T14:00:00"
                },
                {
                    "status": "cancelled",
                    "cancellation_reason": "Cliente solicitou reagendamento"
                },
                {
                    "notes": "Cliente pediu para focar em estratégia de Instagram"
                }
            ]
        }
    }


class AppointmentResponse(BaseModel):
    """Schema para retornar agendamento."""
    
    id: UUID
    client_id: UUID
    scheduled_at: datetime
    duration_minutes: int
    meeting_type: Optional[str]
    status: str
    notes: Optional[str]
    cancelled_at: Optional[datetime]
    cancellation_reason: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "770e8400-e29b-41d4-a716-446655440002",
                "client_id": "660e8400-e29b-41d4-a716-446655440001",
                "scheduled_at": "2025-12-25T10:00:00",
                "duration_minutes": 60,
                "meeting_type": "Diagnóstico inicial",
                "status": "confirmed",
                "notes": "Primeira reunião",
                "cancelled_at": None,
                "cancellation_reason": None,
                "created_at": "2025-12-20T08:00:00",
                "updated_at": "2025-12-20T08:00:00"
            }
        }
    }


class AppointmentStatusUpdate(BaseModel):
    """Schema para atualizar apenas o status do agendamento."""
    
    status: str = Field(
        ...,
        description="Novo status (PENDING, CONFIRMED, COMPLETED, CANCELLED)"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "CONFIRMED"
            }
        }
    }


class AppointmentCancel(BaseModel):
    """Schema para cancelar um agendamento."""
    
    cancellation_reason: Optional[str] = Field(
        None,
        max_length=200,
        description="Motivo do cancelamento (opcional)"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "cancellation_reason": "Cliente solicitou reagendamento"
            }
        }
    }
