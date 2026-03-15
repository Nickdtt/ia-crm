"""
Testes para funcionalidades de bloqueio de agendamentos.

Testa:
- get_available_slots (horários livres)
- block_full_day (bloquear dia inteiro)
- block_shift (bloquear turno)
- unblock_date (desbloquear)
"""

import pytest
from datetime import date, datetime, time
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.appointmentService import (
    get_available_slots,
    block_full_day,
    block_shift,
    unblock_date,
    create_appointment
)
from app.models.appointment import Appointment, AppointmentStatus
from app.models.client import Client, ClientSegment
from app.schemas.appointmentSchema import AppointmentCreate
from decimal import Decimal
import uuid


@pytest.mark.asyncio
async def test_get_available_slots_dia_util_vazio(db: AsyncSession):
    """
    Testa que dia útil sem agendamentos retorna 7 slots.
    
    Esperado: [09:00, 10:00, 11:00, 14:00, 15:00, 16:00, 17:00]
    """
    target_date = date(2026, 1, 26)  # Segunda-feira
    
    slots = await get_available_slots(target_date, db)
    
    assert len(slots) == 7
    assert "09:00" in slots
    assert "10:00" in slots
    assert "11:00" in slots
    # Almoço não aparece
    assert "12:00" not in slots
    assert "13:00" not in slots
    # Tarde
    assert "14:00" in slots
    assert "15:00" in slots
    assert "16:00" in slots
    assert "17:00" in slots


@pytest.mark.asyncio
async def test_get_available_slots_fim_de_semana(db: AsyncSession):
    """
    Testa que fim de semana retorna lista vazia.
    """
    sabado = date(2026, 1, 24)
    domingo = date(2026, 1, 25)
    
    slots_sab = await get_available_slots(sabado, db)
    slots_dom = await get_available_slots(domingo, db)
    
    assert slots_sab == []
    assert slots_dom == []


@pytest.mark.asyncio
async def test_get_available_slots_com_agendamentos(db: AsyncSession):
    """
    Testa que horários ocupados não aparecem nos slots.
    """
    # 1. Criar cliente
    client = Client(
        id=uuid.uuid4(),
        first_name="João",
        last_name="Silva",
        phone="71999999999",
        segment=ClientSegment.CLINICA_ODONTOLOGICA,
        monthly_budget=Decimal("5000.00"),
        main_marketing_problem="Teste"
    )
    db.add(client)
    await db.commit()
    
    # 2. Criar appointment às 10h
    target_date = date(2026, 1, 27)
    appointment = Appointment(
        id=uuid.uuid4(),
        client_id=client.id,
        scheduled_at=datetime.combine(target_date, time(10, 0)),
        duration_minutes=60,
        status=AppointmentStatus.PENDING
    )
    db.add(appointment)
    await db.commit()
    
    # 3. Buscar slots disponíveis
    slots = await get_available_slots(target_date, db)
    
    # 4. Verificar que 10h não aparece
    assert "10:00" not in slots
    assert "09:00" in slots
    assert "11:00" in slots
    assert len(slots) == 6  # 7 - 1 ocupado


@pytest.mark.asyncio
async def test_block_full_day(db: AsyncSession):
    """
    Testa bloqueio de dia inteiro.
    
    Após bloquear, get_available_slots deve retornar [].
    """
    target_date = date(2026, 1, 28)
    
    # 1. Antes do bloqueio: dia tem slots
    slots_antes = await get_available_slots(target_date, db)
    assert len(slots_antes) == 7
    
    # 2. Bloquear dia inteiro
    await block_full_day(target_date, db)
    
    # 3. Depois do bloqueio: sem slots
    slots_depois = await get_available_slots(target_date, db)
    assert slots_depois == []


@pytest.mark.asyncio
async def test_block_shift_morning(db: AsyncSession):
    """
    Testa bloqueio de turno manhã.
    
    Após bloquear manhã, apenas tarde deve estar disponível.
    """
    target_date = date(2026, 1, 29)
    
    # 1. Bloquear manhã
    await block_shift(target_date, "morning", db)
    
    # 2. Buscar slots
    slots = await get_available_slots(target_date, db)
    
    # 3. Verificar: apenas tarde disponível
    assert "09:00" not in slots
    assert "10:00" not in slots
    assert "11:00" not in slots
    assert "14:00" in slots
    assert "15:00" in slots
    assert "16:00" in slots
    assert "17:00" in slots
    assert len(slots) == 4


@pytest.mark.asyncio
async def test_block_shift_afternoon(db: AsyncSession):
    """
    Testa bloqueio de turno tarde.
    
    Após bloquear tarde, apenas manhã deve estar disponível.
    """
    target_date = date(2026, 1, 30)
    
    # 1. Bloquear tarde
    await block_shift(target_date, "afternoon", db)
    
    # 2. Buscar slots
    slots = await get_available_slots(target_date, db)
    
    # 3. Verificar: apenas manhã disponível
    assert "09:00" in slots
    assert "10:00" in slots
    assert "11:00" in slots
    assert "14:00" not in slots
    assert "15:00" not in slots
    assert "16:00" not in slots
    assert "17:00" not in slots
    assert len(slots) == 3


@pytest.mark.asyncio
async def test_block_shift_invalid(db: AsyncSession):
    """
    Testa que shift inválido levanta ValueError.
    """
    target_date = date(2026, 1, 31)
    
    with pytest.raises(ValueError, match="shift deve ser 'morning' ou 'afternoon'"):
        await block_shift(target_date, "night", db)


@pytest.mark.asyncio
async def test_unblock_date(db: AsyncSession):
    """
    Testa desbloqueio de data.
    
    Após desbloquear, slots devem voltar ao normal.
    """
    target_date = date(2026, 2, 3)
    
    # 1. Bloquear dia inteiro
    await block_full_day(target_date, db)
    slots_bloqueado = await get_available_slots(target_date, db)
    assert slots_bloqueado == []
    
    # 2. Desbloquear
    await unblock_date(target_date, db)
    
    # 3. Verificar que voltou ao normal
    slots_desbloqueado = await get_available_slots(target_date, db)
    assert len(slots_desbloqueado) == 7


@pytest.mark.asyncio
async def test_unblock_date_remove_multiplos_bloqueios(db: AsyncSession):
    """
    Testa que unblock_date remove todos os tipos de bloqueio.
    """
    target_date = date(2026, 2, 4)
    
    # 1. Bloquear manhã E tarde separadamente
    await block_shift(target_date, "morning", db)
    await block_shift(target_date, "afternoon", db)
    
    slots_bloqueados = await get_available_slots(target_date, db)
    assert slots_bloqueados == []
    
    # 2. Desbloquear tudo de uma vez
    await unblock_date(target_date, db)
    
    # 3. Verificar que ambos foram removidos
    slots_desbloqueados = await get_available_slots(target_date, db)
    assert len(slots_desbloqueados) == 7


@pytest.mark.asyncio
async def test_bloqueio_nao_afeta_outras_datas(db: AsyncSession):
    """
    Testa que bloqueio de uma data não afeta outras.
    """
    dia1 = date(2026, 2, 5)
    dia2 = date(2026, 2, 6)
    
    # 1. Bloquear apenas dia1
    await block_full_day(dia1, db)
    
    # 2. Verificar que dia1 está bloqueado
    slots_dia1 = await get_available_slots(dia1, db)
    assert slots_dia1 == []
    
    # 3. Verificar que dia2 continua normal
    slots_dia2 = await get_available_slots(dia2, db)
    assert len(slots_dia2) == 7
