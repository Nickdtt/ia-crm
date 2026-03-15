"""
AuthService: Autenticação, hash de senhas e geração de tokens JWT.

Este serviço centraliza:
- Hash e verificação de senhas (bcrypt)
- Autenticação de usuários (email + senha)
- Geração de tokens JWT (access tokens)
- Validação de tokens JWT
"""

import jwt
import bcrypt
from uuid import UUID
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.core.config import get_settings

settings = get_settings()


def hash_password(password: str) -> str:
    """
    Gera hash bcrypt de uma senha.
    
    Args:
        password: Senha em texto plano
        
    Returns:
        str: Hash bcrypt da senha
        
    Exemplo:
        >>> hashed = hash_password("minha_senha_123")
        >>> print(hashed)
        '$2b$12$KIXxP...'
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica se senha corresponde ao hash armazenado.
    
    Args:
        plain_password: Senha em texto plano
        hashed_password: Hash bcrypt armazenado
        
    Returns:
        bool: True se senha válida, False caso contrário
        
    Exemplo:
        >>> is_valid = verify_password("senha123", user.hashed_password)
        >>> if is_valid:
        ...     print("Senha correta!")
    """
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


async def authenticate_user(
    email: str,
    password: str,
    db: AsyncSession
) -> User:
    """
    Autentica usuário por email e senha.
    
    Args:
        email: Email do usuário
        password: Senha em texto plano
        db: Sessão assíncrona do banco
        
    Returns:
        User: Usuário autenticado
        
    Raises:
        ValueError: Se credenciais inválidas ou usuário inativo
        
    Exemplo:
        >>> user = await authenticate_user("admin@agencia.com", "senha123", db)
        >>> print(f"Autenticado: {user.email}")
    """
    from app.services.userService import get_user_by_email
    
    # 1. Buscar usuário por email
    user = await get_user_by_email(email, db)
    
    if not user:
        raise ValueError("Email ou senha incorretos")
    
    # 2. Verificar se usuário está ativo
    if not user.is_active:
        raise ValueError("Usuário inativo")
    
    # 3. Verificar senha usando bcrypt
    if not verify_password(password, user.hashed_password):
        raise ValueError("Email ou senha incorretos")
    
    return user


def create_access_token(
    user_id: UUID,
    expires_delta_minutes: int = None
) -> str:
    """
    Cria JWT com user_id.
    
    Args:
        user_id: UUID do usuário
        expires_delta_minutes: Duração em minutos (default: ACCESS_TOKEN_EXPIRE_MINUTES)
        
    Returns:
        str: Token JWT assinado
        
    Exemplo - Access token (30 min):
        >>> token = create_access_token(user.id)
        >>> print(token)
        'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
        
    Exemplo - Refresh token (7 dias):
        >>> token = create_access_token(user.id, expires_delta_minutes=10080)
        >>> # 7 dias = 7 * 24 * 60 = 10080 minutos
        
    Nota:
        Token expira em ACCESS_TOKEN_EXPIRE_MINUTES (configurado no .env) se expires_delta_minutes for None.
        Payload contém:
        - sub: user_id (UUID como string)
        - exp: timestamp de expiração
    """
    # Se não especificar duração, usa padrão do .env (30 min)
    if expires_delta_minutes is None:
        expires_delta_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
    
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_delta_minutes)
    
    payload = {
        "sub": str(user_id),  # "subject" = user_id (JWT padrão)
        "exp": expire  # expiration timestamp (JWT padrão)
    }
    
    token = jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return token


def verify_token(token: str) -> dict:
    """
    Valida e decodifica JWT.
    
    Args:
        token: Token JWT string
        
    Returns:
        dict: Payload decodificado com 'sub' (user_id) e 'role'
        
    Raises:
        ValueError: Se token inválido ou expirado
        
    Exemplo:
        >>> payload = verify_token(token)
        >>> user_id = payload["sub"]  # "a124309d-7fd0-4f44-8224-36c6673f563a"
        
    Nota:
        PyJWT valida automaticamente:
        - Assinatura (SECRET_KEY)
        - Expiração (exp claim)
        - Algoritmo (ALGORITHM)
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
        
    except jwt.InvalidTokenError as e:
        raise ValueError(f"Token inválido: {str(e)}")
