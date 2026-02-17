"""
userControllers.py

Controller de usuários: endpoints CRUD para gerenciamento de usuários.
Regras de acesso: Todos os endpoints exigem autenticação
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
import uuid

from app.api.dependencies import get_db, get_current_user
from app.schemas.userSchema import UserResponse, UserCreate, UserUpdate
from app.models.user import User
from app.services.authService import hash_password
from app.services.userService import get_user_by_id, get_user_by_email, update_user, delete_user, create_user


router = APIRouter(prefix="/users", tags=["users"])

@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_new_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Cria um novo usuário no sistema.
    
    - **Acesso:** Usuário autenticado
    - **Dados obrigatórios:** email, password

    Returns:
        Usuário criado (UserResponse)
    Raises:
        400 se email já estiver cadastrado
    """
    try:
        user = await create_user(data, db)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/",
    response_model=list[UserResponse]
)
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Lista todos os usuários ativos do sistema.
    
    - **Acesso:** Usuário autenticado

    Returns:
        Lista de usuários ativos (is_active=True).
    """
    stmt = select(User).where(User.is_active)
    result = await db.execute(stmt)
    users = result.scalars().all()
    return users


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id_endpoint(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Busca usuário por ID.
    
    - **Acesso:** Usuário autenticado
    - **Parâmetros:** user_id (UUID)
    
    Returns:
        UserResponse com dados do usuário.
    Raises:
        404 se usuário não existir.
    """
    target_user = await get_user_by_id(user_id, db)
    
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    return target_user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user_by_id_endpoint(
    user_id: UUID,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Atualiza um usuário por ID.

    - **Acesso:** Usuário autenticado
    - **Parâmetros:** user_id (UUID)
    - **Dados:** Apenas campos fornecidos são atualizados

    Returns:
        UserResponse com dados atualizados.
    Raises:
        404 se usuário não existir.
        400 se email já estiver cadastrado.
    """
    target_user = await get_user_by_id(user_id, db)

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )

    # Atualizar usuário (delegar para service)
    try:
        updated_user = await update_user(user_id, data, db)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    return updated_user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_by_id_endpoint(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Remove um usuário por ID (soft delete).

    - **Acesso:** Usuário autenticado
    - **Parâmetros:** user_id (UUID)
    - **Nota:** Soft delete (marca is_active=False)

    Returns:
        204 No Content em caso de sucesso.
    Raises:
        404 se usuário não existir.
    """
    target_user = await get_user_by_id(user_id, db)

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )

    # Delegar remoção ao service
    await delete_user(user_id, db)
    return None
