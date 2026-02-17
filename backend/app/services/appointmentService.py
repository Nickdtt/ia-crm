import uuid
from datetime import datetime, timezone, date, time
from uuid import UUID
from typing import List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from zoneinfo import ZoneInfo

from app.models.appointment import Appointment, AppointmentStatus
from app.models.client import Client
from app.schemas.appointmentSchema import AppointmentCreate, AppointmentUpdate

# Timezone do Brasil
BRAZIL_TZ = ZoneInfo("America/Sao_Paulo")


async def create_appointment(
    data: AppointmentCreate,
    db: AsyncSession,
) -> Appointment:
    """
    Cria um novo agendamento de reunião com cliente.
    
    Validações:
    - Cliente existe
    - Data é futura
    - Horário não está ocupado (ignora agendamentos cancelados)
    
    Args:
        data: AppointmentCreate com client_id, scheduled_at, duration_minutes, 
              meeting_type, notes
        db: AsyncSession
        
    Returns:
        Appointment: Agendamento criado
        
    Raises:
        ValueError: Se cliente não existir, data for passada ou horário estiver ocupado
    """
    # 1. Validar que cliente existe
    client = await db.get(Client, data.client_id)
    if not client:
        raise ValueError("Cliente não encontrado")
    
    # 2. Validar que não é retroativo (já validado no schema, mas reforça)
    now = datetime.now(timezone.utc)
    scheduled = data.scheduled_at.replace(tzinfo=timezone.utc) if data.scheduled_at.tzinfo is None else data.scheduled_at
    if scheduled < now:
        raise ValueError("Não é possível agendar no passado")
    
    # 3. Validar que horário está livre (ignora agendamentos cancelados)
    conflict_check = await db.execute(
        select(Appointment).where(
            Appointment.scheduled_at == data.scheduled_at,
            Appointment.status != AppointmentStatus.CANCELLED
        )
    )
    existing_appointment = conflict_check.scalar_one_or_none()
    
    if existing_appointment:
        raise ValueError("Este horário já está ocupado. Por favor, escolha outro horário.")
    
    # 4. Criar Appointment
    appointment = Appointment(
        id=uuid.uuid4(),
        client_id=data.client_id,
        scheduled_at=data.scheduled_at,
        duration_minutes=data.duration_minutes,
        meeting_type=data.meeting_type,
        notes=data.notes,
        status=AppointmentStatus.PENDING
    )
    
    # 5. Salvar
    db.add(appointment)
    await db.commit()
    await db.refresh(appointment)
    
    return appointment


async def get_appointment_by_id(
    appointment_id: UUID,
    db: AsyncSession
) -> Appointment | None:
    """
    Busca agendamento por ID.
    
    Args:
        appointment_id: UUID do agendamento
        db: Sessão do banco de dados
        
    Returns:
        Appointment | None: Agendamento encontrado ou None
    """
    result = await db.execute(
        select(Appointment).where(Appointment.id == appointment_id)
    )
    return result.scalar_one_or_none()


async def update_appointment(
    appointment_id: UUID,
    data: AppointmentUpdate,
    db: AsyncSession
) -> Appointment:
    """
    Atualiza informações de um agendamento existente.
    
    Args:
        appointment_id: UUID do agendamento
        data: AppointmentUpdate com campos opcionais
        db: Sessão do banco de dados
        
    Returns:
        Appointment: Agendamento atualizado
        
    Raises:
        ValueError: Se agendamento não existir
    """
    # 1. Buscar agendamento
    appointment = await get_appointment_by_id(appointment_id, db)
    if not appointment:
        raise ValueError("Agendamento não encontrado")
    
    # 2. Atualizar campos fornecidos
    if data.scheduled_at is not None:
        appointment.scheduled_at = data.scheduled_at
    if data.duration_minutes is not None:
        appointment.duration_minutes = data.duration_minutes
    if data.meeting_type is not None:
        appointment.meeting_type = data.meeting_type
    if data.notes is not None:
        appointment.notes = data.notes
    if data.status is not None:
        appointment.status = AppointmentStatus(data.status)
    if data.cancellation_reason is not None:
        appointment.cancellation_reason = data.cancellation_reason
    
    # 3. Salvar
    await db.commit()
    await db.refresh(appointment)
    
    return appointment


async def cancel_appointment(
    appointment_id: UUID,
    reason: str,
    db: AsyncSession
) -> Appointment:
    """
    Cancela um agendamento.
    
    Args:
        appointment_id: UUID do agendamento a cancelar
        reason: Motivo do cancelamento
        db: Sessão do banco de dados
        
    Returns:
        Appointment: Agendamento cancelado
        
    Raises:
        ValueError: Se agendamento não existir ou já estiver cancelado
    """
    appointment = await get_appointment_by_id(appointment_id, db)
    if not appointment:
        raise ValueError("Agendamento não encontrado")
    
    if appointment.status == AppointmentStatus.CANCELLED:
        raise ValueError("Agendamento já está cancelado")
    
    # Cancelar: atualizar status, timestamp e motivo
    appointment.status = AppointmentStatus.CANCELLED
    appointment.cancelled_at = datetime.now()
    appointment.cancellation_reason = reason
    
    await db.commit()
    await db.refresh(appointment)
    
    return appointment


async def update_appointment_status(
    appointment_id: UUID,
    status: AppointmentStatus,
    db: AsyncSession
) -> Appointment:
    """
    Atualiza status de um agendamento.
    
    Args:
        appointment_id: UUID do agendamento
        status: Novo status (PENDING, CONFIRMED, COMPLETED, CANCELLED)
        db: Sessão do banco de dados
        
    Returns:
        Appointment: Agendamento atualizado
        
    Raises:
        ValueError: Se agendamento não existir ou transição inválida
    """
    appointment = await get_appointment_by_id(appointment_id, db)
    if not appointment:
        raise ValueError("Agendamento não encontrado")
    
    # Validar transições de status
    if appointment.status == AppointmentStatus.CANCELLED:
        raise ValueError("Não é possível alterar status de agendamento cancelado")
    
    if status == AppointmentStatus.COMPLETED and appointment.scheduled_at > datetime.now():
        raise ValueError("Não é possível marcar como completado reunião futura")
    
    appointment.status = status
    
    await db.commit()
    await db.refresh(appointment)
    
    return appointment


async def list_appointments_by_client(
    client_id: UUID,
    db: AsyncSession
) -> list[Appointment]:
    """
    Lista todos os agendamentos de um cliente específico.
    
    Args:
        client_id: UUID do cliente
        db: Sessão do banco de dados
        
    Returns:
        list[Appointment]: Lista de agendamentos do cliente (ordenados por data)
    """
    stmt = select(Appointment).where(
        Appointment.client_id == client_id
    ).order_by(Appointment.scheduled_at.desc())
    
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_all_appointments(
    db: AsyncSession,
    status: AppointmentStatus | None = None
) -> list[Appointment]:
    """
    Lista todos os agendamentos (para admin).
    
    Args:
        db: Sessão do banco de dados
        status: Filtrar por status específico (opcional)
        
    Returns:
        list[Appointment]: Lista de todos os agendamentos (ordenados por data)
    """
    stmt = select(Appointment)
    
    if status:
        stmt = stmt.where(Appointment.status == status)
    
    stmt = stmt.order_by(Appointment.scheduled_at.desc())
    
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_available_slots(
    target_date: date,
    db: AsyncSession
) -> List[str]:
    """
    Retorna horários livres em uma data específica.
    
    Horário comercial:
    - Segunda a sexta: 9h-12h (manhã) e 14h-18h (tarde)
    - Almoço: 12h-14h (indisponível)
    - Fim de semana: fechado
    
    Args:
        target_date: Data para buscar slots disponíveis
        db: Sessão do banco de dados
        
    Returns:
        List[str]: Lista de horários no formato "HH:MM"
        
    Example:
        >>> await get_available_slots(date(2026, 1, 27), db)
        ["09:00", "10:00", "11:00", "14:00", "15:00", "16:00", "17:00"]
    """
    # 1. Valida dia útil (segunda a sexta)
    if target_date.weekday() >= 5:  # 5=sábado, 6=domingo
        return []
    
    # 2. Verifica se o dia inteiro está bloqueado
    blocked_day = await db.execute(
        select(Appointment)
        .where(
            func.date(Appointment.scheduled_at) == target_date,
            Appointment.client_id.is_(None),  # Bloqueio administrativo
            Appointment.meeting_type == "FULL_DAY_BLOCK"
        )
    )
    if blocked_day.scalar_one_or_none():
        return []
    
    # 3. Gera slots: 9h-12h (manhã) + 14h-18h (tarde)
    all_slots = []
    
    # Verifica se manhã está bloqueada
    morning_blocked = await db.execute(
        select(Appointment)
        .where(
            func.date(Appointment.scheduled_at) == target_date,
            Appointment.client_id.is_(None),
            Appointment.meeting_type == "MORNING_BLOCK"
        )
    )
    
    if not morning_blocked.scalar_one_or_none():
        # Manhã: 9h, 10h, 11h
        for hour in range(9, 12):
            slot = datetime.combine(target_date, time(hour, 0)).replace(tzinfo=BRAZIL_TZ)
            all_slots.append(slot)
    
    # Verifica se tarde está bloqueada
    afternoon_blocked = await db.execute(
        select(Appointment)
        .where(
            func.date(Appointment.scheduled_at) == target_date,
            Appointment.client_id.is_(None),
            Appointment.meeting_type == "AFTERNOON_BLOCK"
        )
    )
    
    if not afternoon_blocked.scalar_one_or_none():
        # Tarde: 14h, 15h, 16h, 17h
        for hour in range(14, 18):
            slot = datetime.combine(target_date, time(hour, 0)).replace(tzinfo=BRAZIL_TZ)
            all_slots.append(slot)
    
    # 4. Busca appointments já marcados no dia
    result = await db.execute(
        select(Appointment.scheduled_at)
        .where(
            func.date(Appointment.scheduled_at) == target_date,
            Appointment.status.in_([
                AppointmentStatus.PENDING, 
                AppointmentStatus.CONFIRMED
            ])
        )
    )
    occupied_times = [row[0] for row in result.fetchall()]
    
    # 5. Remove horários ocupados
    available_slots = [
        slot for slot in all_slots 
        if slot not in occupied_times
    ]
    
    # 6. Formata para string "HH:MM"
    return [slot.strftime("%H:%M") for slot in available_slots]


async def block_full_day(
    target_date: date,
    db: AsyncSession
) -> None:
    """
    Bloqueia um dia inteiro para agendamentos.
    
    Útil para: feriados, férias, eventos especiais.
    
    Args:
        target_date: Data a ser bloqueada
        db: Sessão do banco de dados
        
    Example:
        >>> await block_full_day(date(2026, 1, 27), db)
        # Dia 27/01/2026 ficará totalmente indisponível
    """
    # Cria appointment especial marcando dia como bloqueado
    block_marker = Appointment(
        id=uuid.uuid4(),
        client_id=None,  # Sem cliente = bloqueio administrativo
        scheduled_at=datetime.combine(target_date, time(0, 0)),
        duration_minutes=0,
        meeting_type="FULL_DAY_BLOCK",
        notes=f"Dia bloqueado administrativamente",
        status=AppointmentStatus.CANCELLED  # Usa status existente
    )
    
    db.add(block_marker)
    await db.commit()


async def block_shift(
    target_date: date,
    shift: str,  # "morning" ou "afternoon"
    db: AsyncSession
) -> None:
    """
    Bloqueia um turno específico (manhã ou tarde).
    
    Args:
        target_date: Data do bloqueio
        shift: "morning" (9h-12h) ou "afternoon" (14h-18h)
        db: Sessão do banco de dados
        
    Raises:
        ValueError: Se shift não for "morning" ou "afternoon"
        
    Example:
        >>> await block_shift(date(2026, 1, 27), "morning", db)
        # Manhã bloqueada, tarde continua disponível
    """
    if shift not in ["morning", "afternoon"]:
        raise ValueError("shift deve ser 'morning' ou 'afternoon'")
    
    meeting_type = "MORNING_BLOCK" if shift == "morning" else "AFTERNOON_BLOCK"
    shift_name = "Manhã" if shift == "morning" else "Tarde"
    
    block_marker = Appointment(
        id=uuid.uuid4(),
        client_id=None,
        scheduled_at=datetime.combine(target_date, time(0, 0)),
        duration_minutes=0,
        meeting_type=meeting_type,
        notes=f"{shift_name} bloqueada administrativamente",
        status=AppointmentStatus.CANCELLED  # Usa status existente
    )
    
    db.add(block_marker)
    await db.commit()


async def unblock_date(
    target_date: date,
    db: AsyncSession
) -> None:
    """
    Remove bloqueios de uma data (dia inteiro ou turnos).
    
    Args:
        target_date: Data a ser desbloqueada
        db: Sessão do banco de dados
    """
    # Busca todos os bloqueios da data (client_id NULL = bloqueio)
    result = await db.execute(
        select(Appointment)
        .where(
            func.date(Appointment.scheduled_at) == target_date,
            Appointment.client_id.is_(None)
        )
    )
    blocks = result.scalars().all()
    
    # Deleta cada bloqueio encontrado
    for block in blocks:
        await db.delete(block)
    
    await db.commit()
