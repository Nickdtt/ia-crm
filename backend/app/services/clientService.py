import uuid
from typing import Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client import Client
from app.schemas.clientSchema import ClientCreate, ClientUpdate


async def create_client(
    data: ClientCreate,
    db: AsyncSession,
) -> Client:
    """
    Cria um novo cliente lead para agência de marketing.
    
    Args:
        data: ClientCreate com first_name, last_name, phone, email, segment, 
              monthly_budget, main_marketing_problem e company_name (opcional)
        db: AsyncSession
        
    Returns:
        Client: Cliente criado
        
    Raises:
        ValueError: Se já existir cliente com mesmo telefone
    """
    # 1. Verificar se telefone já existe
    stmt = select(Client).where(Client.phone == data.phone)
    existing = await db.scalar(stmt)
    if existing:
        raise ValueError(f"Telefone {data.phone} já cadastrado")
    
    # 2. Criar Client com campos (segment/budget/problem podem ser None para leads via chat)
    client = Client(
        id=uuid.uuid4(),
        first_name=data.first_name,
        last_name=data.last_name,
        phone=data.phone,
        email=data.email,
        company_name=data.company_name,
        segment=data.segment,
        monthly_budget=data.monthly_budget,
        main_marketing_problem=data.main_marketing_problem,
        notes=data.notes
    )
    
    # 3. Salvar
    db.add(client)
    await db.commit()
    await db.refresh(client)
    
    return client


async def get_client_by_id(
    client_id: UUID,
    db: AsyncSession
) -> Client | None:
    """
    Busca um cliente por ID.
    
    Args:
        client_id: UUID do cliente a buscar
        db: Sessão do banco de dados
        
    Returns:
        Client | None: Instância do cliente encontrado ou None se não existir
        
    Examples:
        # Buscar cliente existente
        client = await get_client_by_id(
            client_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
            db=db
        )
        if client:
            print(f"Cliente: {client.full_name}, Telefone: {client.phone}")
        else:
            print("Cliente não encontrado")
    """
    result = await db.execute(
        select(Client).where(Client.id == client_id)
    )
    return result.scalar_one_or_none()


async def update_client(
    client_id: UUID,
    data: ClientUpdate,
    db: AsyncSession
) -> Client:
    """
    Atualiza informações de um cliente existente.
    
    Args:
        client_id: UUID do cliente a atualizar
        data: ClientUpdate com campos opcionais a atualizar
        db: Sessão do banco de dados
        
    Returns:
        Client: Cliente atualizado
        
    Raises:
        ValueError: Se cliente não existir ou telefone duplicado
        
    Examples:
        # Atualizar apenas telefone
        client = await update_client(
            client_id=UUID("123..."),
            data=ClientUpdate(phone="11999887755"),
            db=db
        )
        
        # Atualizar múltiplos campos
        client = await update_client(
            client_id=UUID("123..."),
            data=ClientUpdate(
                first_name="João",
                last_name="Silva Santos",
                email="joao.novo@email.com",
                monthly_budget=8000.00,
                notes="Cliente prioritário"
            ),
            db=db
        )
    """
    # 1. Buscar cliente existente
    client = await get_client_by_id(client_id, db)
    if not client:
        raise ValueError("Cliente não encontrado")
    
    # 2. Se alterando telefone, validar unicidade
    if data.phone and data.phone != client.phone:
        stmt = select(Client).where(Client.phone == data.phone)
        existing = await db.scalar(stmt)
        if existing:
            raise ValueError(f"Telefone {data.phone} já cadastrado")
    
    # 3. Atualizar apenas campos fornecidos
    if data.first_name is not None:
        client.first_name = data.first_name
    if data.last_name is not None:
        client.last_name = data.last_name
    if data.phone is not None:
        client.phone = data.phone
    if data.email is not None:
        client.email = data.email
    if data.company_name is not None:
        client.company_name = data.company_name
    if data.segment is not None:
        client.segment = data.segment
    if data.monthly_budget is not None:
        client.monthly_budget = data.monthly_budget
    if data.main_marketing_problem is not None:
        client.main_marketing_problem = data.main_marketing_problem
    if data.notes is not None:
        client.notes = data.notes
    
    # 4. Salvar alterações
    await db.commit()
    await db.refresh(client)
    
    return client


async def list_clients(
    db: AsyncSession
) -> list[Client]:
    """
    Lista todos os clientes cadastrados.
    
    Args:
        db: Sessão do banco de dados
        
    Returns:
        list[Client]: Lista de todos os clientes
    """
    result = await db.execute(select(Client))
    return list(result.scalars().all())


async def delete_client(
    client_id: UUID,
    db: AsyncSession
) -> bool:
    """
    Deleta permanentemente um cliente (hard delete).
    
    Args:
        client_id: UUID do cliente a deletar
        db: Sessão do banco de dados
        
    Returns:
        bool: True se deletado, False se não encontrado
    """
    client = await get_client_by_id(client_id, db)
    if not client:
        return False
    
    await db.delete(client)
    await db.commit()
    return True


async def get_client_by_phone(
    db: AsyncSession,
    phone: str
) -> Optional[Client]:
    """
    Busca cliente por telefone (identificador primário via WhatsApp).
    
    Usado pelo agente IA no fluxo de qualificação:
    1. Pergunta telefone ao lead
    2. Busca no banco
    3. Se existe → retoma conversa
    4. Se não existe → inicia qualificação completa
    
    Args:
        db: AsyncSession
        phone: Telefone do cliente (busca exata)
        
    Returns:
        Optional[Client]: Cliente encontrado ou None
    """
    stmt = select(Client).where(Client.phone == phone)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
