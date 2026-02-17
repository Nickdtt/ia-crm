from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from uuid import UUID


class UserCreate(BaseModel):
    """Schema para criar novo usuário administrativo."""
    
    email: EmailStr = Field(..., description="Email válido do usuário")
    password: str = Field(
        ..., 
        min_length=8, 
        description="Senha com mínimo 8 caracteres"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "admin@agencia.com",
                "password": "senha_super_segura_123"
            }
        }
    }


class UserUpdate(BaseModel):
    """Schema para atualizar dados de usuário existente (campos opcionais)."""
    
    email: EmailStr | None = Field(
        None, 
        description="Novo email (opcional)"
    )
    password: str | None = Field(
        None, 
        min_length=8, 
        description="Nova senha com mínimo 8 caracteres (opcional)"
    )
    is_active: bool | None = Field(
        None,
        description="Status ativo/inativo do usuário (opcional)"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "email": "novo_admin@agencia.com"
                },
                {
                    "password": "nova_senha_segura_456"
                },
                {
                    "is_active": False
                },
                {
                    "email": "novo_admin@agencia.com",
                    "password": "nova_senha_segura_456"
                }
            ]
        }
    }


class UserResponse(BaseModel):
    """Schema para retornar dados de usuário (sem password)."""
    
    id: UUID
    email: str
    is_active: bool
    created_at: datetime
    
    model_config = {
        "from_attributes": True,  # Permite criar a partir de models ORM
        "json_schema_extra": {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "admin@agencia.com",
                "is_active": True,
                "created_at": "2025-12-21T10:30:00"
            }
        }
    }
