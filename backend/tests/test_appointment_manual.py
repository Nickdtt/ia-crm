"""
Script manual para testar o model Appointment.

Testa:
- Criação de appointment vinculado a client
- Status transitions
- Duration default (60 min)
- Property is_active

Execute: python test_appointment_manual.py
"""
import asyncio
import sys
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.client import Client, ClientSegment
from app.models.appointment import Appointment, AppointmentStatus


async def setup_client():
    """Cria um client para usar nos testes"""
    async with AsyncSessionLocal() as session:
        client = Client(
            first_name="Carlos",
            last_name="Mendes",
            phone="+5511966666666",
            email="carlos@clinica.com",
            company_name="Clínica Odonto Mendes",
            segment=ClientSegment.CLINICA_ODONTOLOGICA,
            monthly_budget=Decimal("8000.00"),
            main_marketing_problem="Preciso atrair mais pacientes particulares"
        )
        
        session.add(client)
        await session.commit()
        await session.refresh(client)
        
        print(f"✅ Client criado: {client.full_name}")
        return client.id


async def test_create_appointment(client_id):
    """Testa criação de appointment"""
    print("\n🧪 Teste 1: Criar Appointment")
    
    async with AsyncSessionLocal() as session:
        # Agendar reunião para daqui 3 dias
        scheduled_time = datetime.now() + timedelta(days=3)
        
        appointment = Appointment(
            client_id=client_id,
            scheduled_at=scheduled_time,
            meeting_type="Inicial",
            notes="Primeira reunião de análise de marketing"
        )
        
        session.add(appointment)
        await session.commit()
        await session.refresh(appointment)
        
        print(f"✅ Appointment criado: {appointment}")
        print(f"   ID: {appointment.id}")
        print(f"   Cliente ID: {appointment.client_id}")
        print(f"   Data: {appointment.scheduled_at}")
        print(f"   Duração: {appointment.duration_minutes} min (default)")
        print(f"   Status: {appointment.status.value}")
        print(f"   É ativo? {appointment.is_active}")
        
        # Verificar default values
        assert appointment.duration_minutes == 60, "Duration deveria ser 60 por padrão"
        assert appointment.status == AppointmentStatus.PENDING, "Status deveria ser PENDING"
        assert appointment.is_active == True, "Appointment deveria estar ativo"
        
        return appointment.id


async def test_appointment_status_flow(appointment_id):
    """Testa mudança de status"""
    print("\n🧪 Teste 2: Fluxo de status")
    
    async with AsyncSessionLocal() as session:
        # Buscar appointment
        result = await session.execute(
            select(Appointment).where(Appointment.id == appointment_id)
        )
        appointment = result.scalar_one()
        
        print(f"Status inicial: {appointment.status.value}")
        assert appointment.is_active == True
        
        # Confirmar
        appointment.status = AppointmentStatus.CONFIRMED
        await session.commit()
        print(f"✅ Status alterado para: {appointment.status.value}")
        assert appointment.is_active == True
        
        # Completar
        appointment.status = AppointmentStatus.COMPLETED
        await session.commit()
        print(f"✅ Status alterado para: {appointment.status.value}")
        assert appointment.is_active == False, "Completed deveria ser inativo"


async def test_appointment_with_client_relationship(client_id):
    """Testa relacionamento entre appointment e client"""
    print("\n🧪 Teste 3: Relacionamento Client <-> Appointment")
    
    async with AsyncSessionLocal() as session:
        # Buscar client com appointments
        result = await session.execute(
            select(Client).where(Client.id == client_id)
        )
        client = result.scalar_one()
        
        print(f"✅ Client: {client.full_name}")
        print(f"   Total de appointments: {len(client.appointments)}")
        
        for appt in client.appointments:
            print(f"   - {appt.scheduled_at} | Status: {appt.status.value}")


async def test_cancel_appointment(appointment_id):
    """Testa cancelamento de appointment"""
    print("\n🧪 Teste 4: Cancelar appointment")
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Appointment).where(Appointment.id == appointment_id)
        )
        appointment = result.scalar_one()
        
        appointment.status = AppointmentStatus.CANCELLED
        appointment.cancelled_at = datetime.now()
        appointment.cancellation_reason = "Cliente solicitou reagendamento"
        
        await session.commit()
        
        print(f"✅ Appointment cancelado")
        print(f"   Motivo: {appointment.cancellation_reason}")
        print(f"   Cancelado em: {appointment.cancelled_at}")
        print(f"   É ativo? {appointment.is_active}")


async def cleanup():
    """Limpa dados de teste"""
    print("\n🧹 Limpando dados de teste...")
    
    async with AsyncSessionLocal() as session:
        # Deletar clients (cascade delete appointments)
        result = await session.execute(select(Client))
        clients = result.scalars().all()
        
        for client in clients:
            await session.delete(client)
        
        await session.commit()
        print("✅ Dados limpos")


async def main():
    """Executa todos os testes"""
    try:
        client_id = await setup_client()
        appointment_id = await test_create_appointment(client_id)
        await test_appointment_status_flow(appointment_id)
        await test_appointment_with_client_relationship(client_id)
        await test_cancel_appointment(appointment_id)
        
        print("\n✅ TODOS OS TESTES DO MODEL APPOINTMENT PASSARAM!\n")
        
    finally:
        await cleanup()


if __name__ == "__main__":
    asyncio.run(main())
