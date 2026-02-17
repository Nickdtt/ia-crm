"""
Auth Schemas: Requisições e respostas de autenticação.
"""

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Schema para requisição de login."""
    
    email: EmailStr = Field(..., description="Email do usuário")
    password: str = Field(..., min_length=6, max_length=255, description="Senha")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "mdf.nicolas@gmail.com",
                "password": "612662nf"
            }
        }
    }


class TokenResponse(BaseModel):
    """Schema para resposta de autenticação (tokens)."""
    
    access_token: str = Field(..., description="JWT válido por 30 minutos")
    refresh_token: str = Field(..., description="JWT válido por 7 dias")
    token_type: str = Field(default="bearer", description="Tipo de autenticação")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGci...",
                "refresh_token": "eyJhbGci...",
                "token_type": "bearer"
            }
        }
    }


class RefreshRequest(BaseModel):
    """Schema para requisição de refresh de token."""
    
    refresh_token: str = Field(..., description="Refresh token válido")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "refresh_token": "eyJhbGci..."
            }
        }
    }
