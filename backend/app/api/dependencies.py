"""
FastAPI Dependencies: Injeção de dependências para as rotas.

Centraliza as funções de injeção usadas nas rotas:
- get_db: Sessão do banco de dados
- get_current_user: Usuário autenticado via JWT
"""

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.database import get_db
from app.services.authService import verify_token


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
) -> dict:
    """
    Extrai e valida o token JWT do header Authorization.
    
    Esta função:
    1. Recebe o token do header Authorization (formato: "Bearer <token>")
    2. Valida o token usando verify_token() do AuthService
    3. Retorna o payload com user_id (sub)
    
    Args:
        credentials: Token extraído automaticamente pelo HTTPBearer
        
    Returns:
        dict: Payload do token com:
            - "sub": user_id (UUID como string)
            - "exp": timestamp de expiração
            
    Raises:
        HTTPException: Status 401 se token inválido ou expirado
        HTTPException: Status 401 se token ausente
        
    Exemplo:
        # Em uma rota:
        @router.get("/profile")
        async def get_profile(current_user: dict = Depends(get_current_user)):
            user_id = current_user["sub"]
            return {"user_id": user_id}
            
    Nota:
        HTTPBearer extrai automaticamente o token do header Authorization.
        Se não encontrar, FastAPI retorna 403. 
        Se encontrar mas token inválido, retornamos 401 com mensagem clara.
    """
    try:
        # Validar token e obter payload
        payload = verify_token(credentials.credentials)
        return payload
        
    except ValueError as e:
        # Token inválido, expirado ou mal formado
        raise HTTPException(
            status_code=401,
            detail=f"Token inválido: {str(e)}"
        )
