import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.userSchema import UserCreate, UserUpdate
from app.services.authService import hash_password


async def create_user(data: UserCreate, db: AsyncSession) -> User:
    """
    Cria novo usuário administrativo com senha hasheada.
    
    Args:
        data: UserCreate schema com email e password
        db: AsyncSession para operações de banco de dados
        
    Returns:
        User: Instância do usuário criado
        
    Raises:
        ValueError: Se email já existe
    """
    # 1. Verificar se email já existe
    stmt = select(User).where(User.email == data.email)
    existing = await db.scalar(stmt)
    if existing:
        raise ValueError(f"Email {data.email} já cadastrado")
    
    # 2. Hash da senha usando bcrypt (importado de authService)
    hashed_password = hash_password(data.password)
    
    # 3. Criar nova instância User com UUID
    user = User(
        id=uuid.uuid4(),
        email=data.email,
        hashed_password=hashed_password,
        is_active=True
    )
    
    # 4. Adicionar à sessão e commit
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return user


async def get_user_by_id(user_id: uuid.UUID, db: AsyncSession) -> Optional[User]:
    """
    Busca um usuário pelo ID.
    
    Args:
        user_id: UUID do usuário a ser buscado
        db: AsyncSession para operações de banco de dados
        
    Returns:
        User: Instância do usuário encontrado ou None se não existir
        
    Exemplo:
        user = await get_user_by_id(some_uuid, db)
        if user:
            print(f"Usuário encontrado: {user.email}")
        else:
            print("Usuário não existe")
    """
    # Query simples: SELECT * FROM users WHERE id = ?
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    
    # scalar_one_or_none(): retorna 1 resultado ou None (não levanta exceção)
    return result.scalar_one_or_none()


async def get_user_by_email(email: str, db: AsyncSession) -> Optional[User]:
    """
    Busca um usuário pelo email.
    
    Args:
        email: Email do usuário a ser buscado
        db: AsyncSession para operações de banco de dados
        
    Returns:
        User: Instância do usuário encontrado ou None se não existir
        
    Exemplo:
        user = await get_user_by_email("admin@agencia.com", db)
        if user:
            print(f"Usuário encontrado: {user.id}")
        else:
            print("Email não cadastrado")
    """
    # Query simples: SELECT * FROM users WHERE email = ?
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    
    # scalar_one_or_none(): retorna 1 resultado ou None (não levanta exceção)
    return result.scalar_one_or_none()


async def update_user(
    user_id: uuid.UUID, 
    data: UserUpdate, 
    db: AsyncSession
) -> User:
    """
    Atualiza dados de um usuário existente.
    
    Args:
        user_id: UUID do usuário a ser atualizado
        data: UserUpdate schema com campos opcionais (email, password, is_active)
        db: AsyncSession para operações de banco de dados
        
    Returns:
        User: Instância do usuário atualizado
        
    Raises:
        ValueError: Se usuário não existe ou novo email já está em uso
        
    Exemplo:
        # Atualizar apenas email
        update_data = UserUpdate(email="novo@agencia.com")
        user = await update_user(user_id, update_data, db)
        
        # Atualizar senha
        update_data = UserUpdate(password="novaSenha123")
        user = await update_user(user_id, update_data, db)
        
        # Desativar usuário
        update_data = UserUpdate(is_active=False)
        user = await update_user(user_id, update_data, db)
    """
    # 1. Buscar usuário existente
    user = await get_user_by_id(user_id, db)
    if not user:
        raise ValueError("Usuário não encontrado")
    
    # 2. Se email foi fornecido e mudou, verificar duplicação
    if data.email and data.email != user.email:
        stmt = select(User).where(User.email == data.email)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise ValueError(f"Email {data.email} já está em uso")
        user.email = data.email
    
    # 3. Se senha foi fornecida, fazer hash e atualizar
    if data.password:
        user.hashed_password = hash_password(data.password)
    
    # 4. Se is_active foi fornecido, atualizar
    if data.is_active is not None:
        user.is_active = data.is_active
    
    # 5. Commit e retornar usuário atualizado
    await db.commit()
    await db.refresh(user)
    
    return user


async def delete_user(user_id: uuid.UUID, db: AsyncSession) -> User:
    """
    Deleta (desativa) um usuário - SOFT DELETE.
    
    Marca o usuário como inativo (is_active=False) sem remover do banco.
    Isso preserva histórico e integridade referencial.
    
    Args:
        user_id: UUID do usuário a ser deletado
        db: AsyncSession para operações de banco de dados
        
    Returns:
        User: Instância do usuário com is_active=False
        
    Raises:
        ValueError: Se usuário não existe
        
    Exemplo:
        deleted_user = await delete_user(user_id, db)
        assert deleted_user.is_active == False
        # Usuário ainda existe no DB, mas não pode mais fazer login
    """
    # 1. Buscar usuário existente
    user = await get_user_by_id(user_id, db)
    if not user:
        raise ValueError("Usuário não encontrado")
    
    # 2. Soft delete: marcar como inativo
    user.is_active = False
    
    # 3. Commit e retornar usuário desativado
    await db.commit()
    await db.refresh(user)
    
    return user