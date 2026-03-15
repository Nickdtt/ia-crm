from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.schemas.clientSchema import ClientCreate, ClientUpdate, ClientResponse
from app.services.clientService import (
    create_client,
    get_client_by_id,
    list_clients,
    update_client,
    delete_client
)
from app.api.dependencies import get_current_user

router = APIRouter(
    prefix="/clients",
    tags=["clients"],
    responses={
        401: {"description": "Não autorizado"},
        404: {"description": "Cliente não encontrado"}
    }
)


@router.get("/", response_model=List[ClientResponse])
async def list_clients_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Lista todos os clientes.
    
    - **Acesso:** Usuário autenticado
    - **Retorna:** Lista de clientes
    """
    clients = await list_clients(db)
    return clients


@router.post("/", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client_endpoint(
    client_data: ClientCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Cria um novo cliente.
    
    - **Acesso:** Usuário autenticado
    - **Dados obrigatórios:** first_name, last_name, phone
    - **Dados opcionais:** email, company_name, segment, monthly_budget, main_marketing_problem, notes
    """
    try:
        client = await create_client(client_data, db)
        return client
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client_endpoint(
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Busca um cliente por ID.
    
    - **Acesso:** Usuário autenticado
    - **Parâmetros:** client_id (UUID)
    """
    client = await get_client_by_id(client_id, db)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado"
        )
    return client


@router.put("/{client_id}", response_model=ClientResponse)
async def update_client_endpoint(
    client_id: UUID,
    client_data: ClientUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Atualiza um cliente.
    
    - **Acesso:** Usuário autenticado
    - **Parâmetros:** client_id (UUID)
    - **Dados:** Apenas campos fornecidos são atualizados
    """
    client = await update_client(client_id, client_data, db)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado"
        )
    return client


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client_endpoint(
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Deleta um cliente permanentemente.
    
    - **Acesso:** Usuário autenticado
    - **Parâmetros:** client_id (UUID)
    - **Nota:** Hard delete (remove permanentemente do banco)
    """
    deleted = await delete_client(client_id, db)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado"
        )