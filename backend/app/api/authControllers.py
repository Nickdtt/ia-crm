"""
Auth Router: Endpoints de autenticação.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.api.dependencies import get_db
from app.services.authService import authenticate_user, create_access_token, verify_token
from app.schemas.authSchema import LoginRequest, TokenResponse, RefreshRequest


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Endpoint de login: autentica usuário e retorna tokens JWT.
    
    Returns:
        TokenResponse com access_token (30 min) e refresh_token (7 dias)
    """
    try:
        # Autenticar usuário (verifica email + senha)
        user = await authenticate_user(
            email=request.email,
            password=request.password,
            db=db
        )
        
        # Gerar access token (30 min)
        access_token = create_access_token(user_id=user.id)
        
        # Gerar refresh token (7 dias = 10080 min)
        refresh_token = create_access_token(
            user_id=user.id,
            expires_delta_minutes=10080
        )
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: RefreshRequest) -> dict:
    """
    Endpoint de refresh: gera novo access_token usando refresh_token válido.
    
    Returns:
        TokenResponse com novo access_token e mesmo refresh_token
    """
    try:
        # Validar refresh_token
        payload = verify_token(request.refresh_token)
        
        # Extrair user_id do payload
        user_id = UUID(payload["sub"])
        
        # Gerar novo access token (30 min)
        access_token = create_access_token(user_id=user_id)
        
        return {
            "access_token": access_token,
            "refresh_token": request.refresh_token,
            "token_type": "bearer"
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=401,
            detail=f"Refresh token inválido: {str(e)}"
        )
