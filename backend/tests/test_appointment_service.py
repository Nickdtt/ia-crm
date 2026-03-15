"""
Teste manual do appointmentService simplificado.

Valida:
- create_appointment (sem professional_id/service_id)
- get_appointment_by_id
- update_appointment
- update_appointment_status
- cancel_appointment
- list_appointments_by_client
- list_all_appointments
"""
import asyncio
from datetime import datetime, timedelta
from app.core.database import AsyncSessionLocal
from app.services.appointmentService import (
    create_appointment,
    get_appointment_by_id,
    update_appointment,
    update_appointment_status,
    cancel_appointment,
    list_appointments_by_client,
    list_all_appointments
)
from app.services.clientService import create_client, delete_client
from app.schemas.appointmentSchema import AppointmentCreate, AppointmentUpdate
from app.schemas.clientSchema import ClientCreate
from app.models.appointment import AppointmentStatus
from app.models.client import ClientSegment
from decimal import Decimal


async def test_appointment_service():
    """Testa todas as operações do appointmentService"""
    
    async with AsyncSessionLocal() as db:
        print("=" * 60)
        print("SETUP: Criar cliente para testes")
        print("=" * 60)
        
        try:
            client_data = ClientCreate(
                first_name="Carlos",
                last_name="Mendes",
                phone="11987654321",
                email="carlos@empresa.com",
                segment=ClientSegment.ECOMMERCE_SAUDE,
                monthly_budget=Decimal("10000.00"),
                main_marketing_problem="Baixa conversão no site"
            )
            
            client = await create_client(client_data, db)
            print(f"✅ Cliente criado: {client.full_name} (ID: {client.id})")
            print()
            
            client_id = client.id
            
        except Exception as e:
            print(f"❌ Erro ao criar cliente: {e}")
            return
        
        # ============================================
        print("=" * 60)
        print("TESTE 1: Criar agendamento (estrutura simplificada)")
        print("=" * 60)
        
        try:
            future_date = datetime.now() + timedelta(days=7, hours=2)
            
            appointment_data = AppointmentCreate(
                client_id=client_id,
                scheduled_at=future_date,
                duration_minutes=60,
                meeting_type="Diagnóstico inicial",
                notes="Primeira reunião para entender necessidades"
            )
            
            appointment = await create_appointment(appointment_data, db)
            
            print(f"✅ Agendamento criado com sucesso!")
            print(f"   ID: {appointment.id}")
            print(f"   Cliente ID: {appointment.client_id}")
            print(f"   Data/Hora: {appointment.scheduled_at}")
            print(f"   Duração: {appointment.duration_minutes} minutos")
            print(f"   Tipo: {appointment.meeting_type}")
            print(f"   Status: {appointment.status.value}")
            print(f"   Notas: {appointment.notes}")
            print()
            
            appointment_id = appointment.id
            
        except Exception as e:
            print(f"❌ Erro ao criar agendamento: {e}")
            return
        
        # ============================================
        print("=" * 60)
        print("TESTE 2: Buscar agendamento por ID")
        print("=" * 60)
        
        found = await get_appointment_by_id(appointment_id, db)
        if found:
            print(f"✅ Agendamento encontrado")
            print(f"   Status: {found.status.value}")
            print(f"   Tipo de reunião: {found.meeting_type}")
        else:
            print("❌ Agendamento não encontrado")
        print()
        
        # ============================================
        print("=" * 60)
        print("TESTE 3: Atualizar agendamento")
        print("=" * 60)
        
        try:
            new_date = datetime.now() + timedelta(days=10, hours=3)
            
            update_data = AppointmentUpdate(
                scheduled_at=new_date,
                duration_minutes=90,
                meeting_type="Apresentação de proposta",
                notes="Cliente pediu reunião mais longa para discutir detalhes"
            )
            
            updated = await update_appointment(appointment_id, update_data, db)
            
            print(f"✅ Agendamento atualizado!")
            print(f"   Nova data: {updated.scheduled_at}")
            print(f"   Nova duração: {updated.duration_minutes} min")
            print(f"   Novo tipo: {updated.meeting_type}")
        except Exception as e:
            print(f"❌ Erro ao atualizar: {e}")
        print()
        
        # ============================================
        print("=" * 60)
        print("TESTE 4: Atualizar status do agendamento")
        print("=" * 60)
        
        try:
            confirmed = await update_appointment_status(
                appointment_id,
                AppointmentStatus.CONFIRMED,
                db
            )
            print(f"✅ Status atualizado para: {confirmed.status.value}")
        except Exception as e:
            print(f"❌ Erro ao atualizar status: {e}")
        print()
        
        # ============================================
        print("=" * 60)
        print("TESTE 5: Criar segundo agendamento")
        print("=" * 60)
        
        try:
            future_date2 = datetime.now() + timedelta(days=14)
            
            appointment2_data = AppointmentCreate(
                client_id=client_id,
                scheduled_at=future_date2,
                duration_minutes=60,
                meeting_type="Follow-up",
                notes="Revisar resultados da primeira campanha"
            )
            
            appointment2 = await create_appointment(appointment2_data, db)
            print(f"✅ Segundo agendamento criado")
            print(f"   Data: {appointment2.scheduled_at}")
            print(f"   Tipo: {appointment2.meeting_type}")
            
            appointment2_id = appointment2.id
        except Exception as e:
            print(f"❌ Erro ao criar segundo agendamento: {e}")
            appointment2_id = None
        print()
        
        # ============================================
        print("=" * 60)
        print("TESTE 6: Listar agendamentos por cliente")
        print("=" * 60)
        
        client_appointments = await list_appointments_by_client(client_id, db)
        print(f"✅ Total de agendamentos do cliente: {len(client_appointments)}")
        for idx, apt in enumerate(client_appointments, 1):
            print(f"   {idx}. {apt.scheduled_at} - {apt.meeting_type} - {apt.status.value}")
        print()
        
        # ============================================
        print("=" * 60)
        print("TESTE 7: Listar todos os agendamentos")
        print("=" * 60)
        
        all_appointments = await list_all_appointments(db)
        print(f"✅ Total de agendamentos no sistema: {len(all_appointments)}")
        print()
        
        # ============================================
        print("=" * 60)
        print("TESTE 8: Cancelar agendamento")
        print("=" * 60)
        
        if appointment2_id:
            try:
                cancelled = await cancel_appointment(
                    appointment2_id,
                    "Cliente solicitou reagendamento",
                    db
                )
                print(f"✅ Agendamento cancelado")
                print(f"   Status: {cancelled.status.value}")
                print(f"   Cancelado em: {cancelled.cancelled_at}")
                print(f"   Motivo: {cancelled.cancellation_reason}")
            except Exception as e:
                print(f"❌ Erro ao cancelar: {e}")
        print()
        
        # ============================================
        print("=" * 60)
        print("TESTE 9: Validar data retroativa (deve falhar)")
        print("=" * 60)
        
        try:
            past_date = datetime.now() - timedelta(days=1)
            
            past_appointment = AppointmentCreate(
                client_id=client_id,
                scheduled_at=past_date,  # ❌ Data passada
                duration_minutes=60,
                meeting_type="Teste"
            )
            
            await create_appointment(past_appointment, db)
            print("❌ ERRO: Deveria ter bloqueado data retroativa!")
        except ValueError as e:
            print(f"✅ Validação funcionou: {e}")
        print()
        
        # ============================================
        print("=" * 60)
        print("CLEANUP: Deletar cliente e agendamentos")
        print("=" * 60)
        
        deleted = await delete_client(client_id, db)
        print(f"✅ Cliente deletado: {deleted}")
        print("   (Agendamentos deletados em cascata)")
        
        print()
        print("=" * 60)
        print("✅ TODOS OS TESTES CONCLUÍDOS!")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_appointment_service())
