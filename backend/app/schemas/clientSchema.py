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
    
    segment: ClientSegment = Field(
        ...,
        description="Segmento de atuação (foco em saúde)"
    )
    
    monthly_budget: Decimal = Field(
        ...,
        ge=0,
        max_digits=10,
        decimal_places=2,
        description="Orçamento mensal disponível para marketing (R$)"
    )
    
    main_marketing_problem: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description="Principal problema/desafio de marketing atual"
    )
    
    notes: Optional[str] = Field(
        None,
        max_length=2000,
        description="Observações adicionais"
    )
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Remove caracteres especiais e valida formato básico"""
        cleaned = ''.join(filter(str.isdigit, v))
        if len(cleaned) < 10 or len(cleaned) > 15:
            raise ValueError('Telefone deve ter entre 10 e 15 dígitos')
        return v
    
    @field_validator('monthly_budget')
    @classmethod
    def validate_budget(cls, v: Decimal) -> Decimal:
        """Valida orçamento mínimo para qualificação"""
        if v < Decimal('1000.00'):
            raise ValueError('Orçamento mínimo deve ser R$ 1.000,00')
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
        if v is not None and v < Decimal('1000.00'):
            raise ValueError('Orçamento mínimo deve ser R$ 1.000,00')
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
    segment: ClientSegment
    monthly_budget: Decimal
    main_marketing_problem: str
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
