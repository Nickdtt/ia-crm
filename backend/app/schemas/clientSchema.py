from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from typing import Optional
from app.models.client import ClientSegment


class ClientCreate(BaseModel):
    """Schema para criar novo cliente de marketing."""
    
    first_name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Primeiro nome do cliente"
    )
    
    last_name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Sobrenome do cliente"
    )
    
    phone: str = Field(
        ...,
        min_length=11,
        max_length=20,
        description="Telefone/WhatsApp com DDD (ex: +5511987654321)"
    )
    
    email: Optional[EmailStr] = Field(
        None,
        description="Email do cliente (opcional)"
    )
    
    company_name: Optional[str] = Field(
        None,
        max_length=255,
        description="Nome da empresa (opcional para autônomos PF)"
    )
    
    segment: Optional[ClientSegment] = Field(
        None,
        description="Segmento de atuação (foco em saúde). Opcional para leads via chat."
    )
    
    monthly_budget: Optional[Decimal] = Field(
        None,
        ge=0,
        max_digits=10,
        decimal_places=2,
        description="Orçamento mensal disponível para marketing (R$). Opcional para leads via chat."
    )
    
    main_marketing_problem: Optional[str] = Field(
        None,
        min_length=10,
        max_length=1000,
        description="Principal problema/desafio de marketing atual. Opcional para leads via chat."
    )
    
    notes: Optional[str] = Field(
        None,
        max_length=2000,
        description="Observações adicionais"
    )
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Valida formato: telefone (10-15 dígitos) ou web-{id} (leads via chat)"""
        if v.startswith('web-'):
            return v  # Leads do chat usam web-{session_id[:8]}
        cleaned = ''.join(filter(str.isdigit, v))
        if len(cleaned) < 10 or len(cleaned) > 15:
            raise ValueError('Telefone deve ter entre 10 e 15 dígitos')
        return v
    
    @field_validator('monthly_budget')
    @classmethod
    def validate_budget(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        """Valida orçamento mínimo (quando informado)"""
        if v is not None and v < Decimal('0'):
            raise ValueError('Orçamento não pode ser negativo')
        return v
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "first_name": "João",
                "last_name": "Silva",
                "phone": "+5511987654321",
                "email": "joao@clinicasilva.com.br",
                "company_name": "Clínica Silva",
                "segment": "clinica_medica",
                "monthly_budget": 7500.00,
                "main_marketing_problem": "Baixa taxa de conversão no Instagram",
                "notes": "Cliente indicado por parceiro"
            }
        }
    )


class ClientUpdate(BaseModel):
    """Schema para atualização parcial de Client."""
    
    first_name: Optional[str] = Field(None, min_length=2, max_length=100)
    last_name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone: Optional[str] = Field(None, min_length=11, max_length=20)
    email: Optional[EmailStr] = None
    company_name: Optional[str] = Field(None, max_length=255)
    segment: Optional[ClientSegment] = None
    monthly_budget: Optional[Decimal] = Field(None, ge=0)
    main_marketing_problem: Optional[str] = Field(None, min_length=10, max_length=1000)
    notes: Optional[str] = Field(None, max_length=2000)
    
    @field_validator('monthly_budget')
    @classmethod
    def validate_budget(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v < Decimal('0'):
            raise ValueError('Orçamento não pode ser negativo')
        return v
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "monthly_budget": 10000.00,
                "notes": "Aumentou orçamento após primeira reunião"
            }
        }
    )


class ClientResponse(BaseModel):
    """Schema de resposta com dados do cliente."""
    
    id: UUID
    first_name: str
    last_name: str
    phone: str
    email: Optional[EmailStr]
    company_name: Optional[str]
    segment: Optional[ClientSegment]
    monthly_budget: Optional[Decimal]
    main_marketing_problem: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
