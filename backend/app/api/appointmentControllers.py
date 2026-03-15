"""
appointmentControllers.py

Controller de agendamentos: endpoints CRUD para gerenciamento de reuniões.
Todos os endpoints exigem autenticação.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
from datetime import date
from pydantic import BaseModel

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.schemas.appointmentSchema import (
    AppointmentCreate,
    AppointmentUpdate,
    AppointmentResponse,
    AppointmentStatusUpdate,
    AppointmentCancel
)
from app.services.appointmentService import (
    create_appointment,
    get_appointment_by_id,
    list_all_appointments,
    list_appointments_by_client,
    update_appointment,
    cancel_appointment,
    update_appointment_status,
    block_full_day,
    block_shift,
    unblock_date
)


router = APIRouter(
    prefix="/appointments",
    tags=["appointments"],
    responses={
        401: {"description": "Não autorizado"},
        404: {"description": "Agendamento não encontrado"}
    }
)


@router.get("/", response_model=List[AppointmentResponse])
async def list_appointments_endpoint(
    client_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Lista agendamentos do sistema.
    
    - **Acesso:** Usuário autenticado
    - **Parâmetros opcionais:**
        - client_id: Filtra agendamentos de um cliente específico
    - **Retorna:** Lista de agendamentos (todos ou filtrados por cliente)
    """
    if client_id:
        appointments = await list_appointments_by_client(client_id, db)
    else:
        appointments = await list_all_appointments(db)
    
    return appointments


@router.post("/", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
async def create_appointment_endpoint(
    appointment_data: AppointmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Cria um novo agendamento.
    
    - **Acesso:** Usuário autenticado
    - **Dados obrigatórios:** client_id, scheduled_at
    - **Dados opcionais:** duration_minutes, meeting_type, notes
    - **Validações:**
        - client_id deve existir
        - scheduled_at deve ser data futura
    """
    try:
        appointment = await create_appointment(appointment_data, db)
        return appointment
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{appointment_id}", response_model=AppointmentResponse)
async def get_appointment_endpoint(
    appointment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Busca um agendamento por ID.
    
    - **Acesso:** Usuário autenticado
    - **Parâmetros:** appointment_id (UUID)
    """
    appointment = await get_appointment_by_id(appointment_id, db)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agendamento não encontrado"
        )
    return appointment


@router.put("/{appointment_id}", response_model=AppointmentResponse)
async def update_appointment_endpoint(
    appointment_id: UUID,
    appointment_data: AppointmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Atualiza um agendamento.
    
    - **Acesso:** Usuário autenticado
    - **Parâmetros:** appointment_id (UUID)
    - **Dados:** Apenas campos fornecidos são atualizados
    - **Validações:**
        - scheduled_at (se fornecido) deve ser data futura
    """
    try:
        appointment = await update_appointment(appointment_id, appointment_data, db)
        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agendamento não encontrado"
            )
        return appointment
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.patch("/{appointment_id}/cancel", response_model=AppointmentResponse)
async def cancel_appointment_endpoint(
    appointment_id: UUID,
    cancel_data: AppointmentCancel,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Cancela um agendamento.
    
    - **Acesso:** Usuário autenticado
    - **Parâmetros:** appointment_id (UUID)
    - **Dados opcionais:** cancellation_reason (motivo do cancelamento)
    - **Efeitos:**
        - status → CANCELLED
        - cancelled_at → timestamp atual
        - cancellation_reason → motivo fornecido
    """
    try:
        appointment = await cancel_appointment(
            appointment_id,
            cancel_data.cancellation_reason,
            db
        )
        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agendamento não encontrado"
            )
        return appointment
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.patch("/{appointment_id}/status", response_model=AppointmentResponse)
async def update_status_endpoint(
    appointment_id: UUID,
    status_data: AppointmentStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Atualiza o status de um agendamento.
    
    - **Acesso:** Usuário autenticado
    - **Parâmetros:** appointment_id (UUID)
    - **Dados obrigatórios:** status (PENDING, CONFIRMED, COMPLETED, CANCELLED)
    - **Validações:**
        - Transições de status inválidas são bloqueadas
        - Status CANCELLED não pode ser alterado
    """
    try:
        appointment = await update_appointment_status(
            appointment_id,
            status_data.status,
            db
        )
        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agendamento não encontrado"
            )
        return appointment
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# Schemas para bloqueios
class BlockFullDayRequest(BaseModel):
    date: date

class BlockShiftRequest(BaseModel):
    date: date
    shift: str  # "morning" ou "afternoon"


@router.post("/block/full-day", status_code=status.HTTP_204_NO_CONTENT)
async def block_full_day_endpoint(
    data: BlockFullDayRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Bloqueia um dia inteiro para agendamentos (admin only).
    
    Útil para: feriados, férias, eventos especiais.
    
    - **Acesso:** Apenas admin
    - **Parâmetros:** date (YYYY-MM-DD)
    - **Efeito:** Nenhum horário do dia ficará disponível
    
    Exemplo:
    ```json
    {"date": "2026-12-25"}
    ```
    """
    try:
        await block_full_day(data.date, db)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/block/shift", status_code=status.HTTP_204_NO_CONTENT)
async def block_shift_endpoint(
    data: BlockShiftRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Bloqueia um turno específico (manhã ou tarde) para agendamentos (admin only).
    
    - **Acesso:** Apenas admin
    - **Parâmetros:**
        - date (YYYY-MM-DD)
        - shift ("morning" para 9h-12h ou "afternoon" para 14h-18h)
    
    Exemplo:
    ```json
    {"date": "2026-01-27", "shift": "morning"}
    ```
    """
    try:
        await block_shift(data.date, data.shift, db)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/block/{target_date}", status_code=status.HTTP_204_NO_CONTENT)
async def unblock_date_endpoint(
    target_date: date,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Remove todos os bloqueios de uma data (admin only).
    
    Remove bloqueios de dia inteiro e de turnos, liberando a data para agendamentos.
    
    - **Acesso:** Apenas admin
    - **Parâmetros:** target_date (YYYY-MM-DD) na URL
    
    Exemplo:
    ```
    DELETE /api/v1/appointments/block/2026-01-27
    ```
    """
    try:
        await unblock_date(target_date, db)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
