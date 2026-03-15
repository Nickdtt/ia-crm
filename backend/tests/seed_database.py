"""
Teste que MANTÉM dados no banco para visualização no DBeaver.
Popula o banco com dados de exemplo sem fazer cleanup.
"""
import asyncio
from decimal import Decimal
from datetime import datetime, timedelta
from app.core.database import AsyncSessionLocal
from app.services.clientService import create_client
from app.services.userService import create_user
from app.services.appointmentService import create_appointment
from app.schemas.clientSchema import ClientCreate
from app.schemas.userSchema import UserCreate
from app.schemas.appointmentSchema import AppointmentCreate
from app.models.client import ClientSegment


async def seed_database():
    """Popula banco com dados de exemplo (SEM deletar)"""
    
    async with AsyncSessionLocal() as db:
        print("=" * 60)
        print("📝 CRIANDO DADOS DE EXEMPLO NO BANCO")
        print("=" * 60)
        print()
        
        # ============================================
        print("1️⃣  CRIANDO USUÁRIO ADMIN")
        print("-" * 60)
        
        try:
            admin = await create_user(UserCreate(
                email="admin@agencia.com",
                password="Admin123"
            ), db)
            print(f"✅ Admin criado: {admin.email}")
            print(f"   ID: {admin.id}")
            print(f"   Senha: Admin123")
        except Exception as e:
            print(f"⚠️  Admin já existe ou erro: {e}")
        print()
        
        # ============================================
        print("2️⃣  CRIANDO CLIENTES")
        print("-" * 60)
        
        # Cliente 1 - Clínica Odontológica
        client1 = await create_client(ClientCreate(
            first_name="Roberto",
            last_name="Ferreira",
            phone="11999001122",
            email="roberto@clinicadental.com",
            company_name="Clínica Dental Sorriso",
            segment=ClientSegment.CLINICA_ODONTOLOGICA,
            monthly_budget=Decimal("8500.00"),
            main_marketing_problem="Não aparece no Google Maps quando pesquisam dentista",
            notes="Lead qualificado via Instagram - alta prioridade"
        ), db)
        print(f"✅ Cliente 1: {client1.full_name}")
        print(f"   Empresa: {client1.company_name}")
        print(f"   Segmento: {client1.segment.value}")
        print(f"   Orçamento: R$ {client1.monthly_budget}/mês")
        print(f"   Telefone: {client1.phone}")
        print()
        
        # Cliente 2 - Clínica Médica
        client2 = await create_client(ClientCreate(
            first_name="Ana",
            last_name="Costa",
            phone="11988112233",
            email="ana@clinicamed.com",
            company_name="Clínica Médica Saúde Total",
            segment=ClientSegment.CLINICA_MEDICA,
            monthly_budget=Decimal("15000.00"),
            main_marketing_problem="Baixa conversão de leads em pacientes",
            notes="Já investiu em marketing antes, conhece o processo"
        ), db)
        print(f"✅ Cliente 2: {client2.full_name}")
        print(f"   Empresa: {client2.company_name}")
        print(f"   Segmento: {client2.segment.value}")
        print(f"   Orçamento: R$ {client2.monthly_budget}/mês")
        print(f"   Telefone: {client2.phone}")
        print()
        
        # Cliente 3 - E-commerce
        client3 = await create_client(ClientCreate(
            first_name="Carlos",
            last_name="Mendes",
            phone="11977223344",
            email="carlos@farmavida.com",
            company_name="FarmaVida E-commerce",
            segment=ClientSegment.ECOMMERCE_SAUDE,
            monthly_budget=Decimal("12000.00"),
            main_marketing_problem="Alto custo de aquisição no Google Ads",
            notes="Quer otimizar campanhas existentes"
        ), db)
        print(f"✅ Cliente 3: {client3.full_name}")
        print(f"   Empresa: {client3.company_name}")
        print(f"   Segmento: {client3.segment.value}")
        print(f"   Orçamento: R$ {client3.monthly_budget}/mês")
        print(f"   Telefone: {client3.phone}")
        print()
        
        # ============================================
        print("3️⃣  CRIANDO AGENDAMENTOS")
        print("-" * 60)
        
        # Agendamento 1 - Cliente 1
        apt1 = await create_appointment(AppointmentCreate(
            client_id=client1.id,
            scheduled_at=datetime.now() + timedelta(days=3, hours=10),
            duration_minutes=60,
            meeting_type="Diagnóstico inicial",
            notes="Primeira reunião - focar em SEO local e Google Meu Negócio"
        ), db)
        print(f"✅ Agendamento 1:")
        print(f"   Cliente: {client1.full_name}")
        print(f"   Data/Hora: {apt1.scheduled_at}")
        print(f"   Tipo: {apt1.meeting_type}")
        print(f"   Status: {apt1.status.value}")
        print()
        
        # Agendamento 2 - Cliente 2
        apt2 = await create_appointment(AppointmentCreate(
            client_id=client2.id,
            scheduled_at=datetime.now() + timedelta(days=7, hours=14),
            duration_minutes=90,
            meeting_type="Apresentação de proposta",
            notes="Cliente quer campanha completa: Google Ads + SEO + Redes Sociais"
        ), db)
        print(f"✅ Agendamento 2:")
        print(f"   Cliente: {client2.full_name}")
        print(f"   Data/Hora: {apt2.scheduled_at}")
        print(f"   Tipo: {apt2.meeting_type}")
        print(f"   Status: {apt2.status.value}")
        print()
        
        # Agendamento 3 - Cliente 3
        apt3 = await create_appointment(AppointmentCreate(
            client_id=client3.id,
            scheduled_at=datetime.now() + timedelta(days=5, hours=16),
            duration_minutes=60,
            meeting_type="Consultoria Google Ads",
            notes="Revisar campanhas atuais e otimizar ROAS"
        ), db)
        print(f"✅ Agendamento 3:")
        print(f"   Cliente: {client3.full_name}")
        print(f"   Data/Hora: {apt3.scheduled_at}")
        print(f"   Tipo: {apt3.meeting_type}")
        print(f"   Status: {apt3.status.value}")
        print()
        
        # ============================================
        print("=" * 60)
        print("✅ DADOS GRAVADOS NO BANCO COM SUCESSO!")
        print("=" * 60)
        print()
        print("📊 RESUMO:")
        print(f"   • 1 usuário admin (admin@agencia.com)")
        print(f"   • 3 clientes criados")
        print(f"   • 3 agendamentos marcados")
        print()
        print("🔍 VISUALIZE NO DBEAVER:")
        print("   Banco: marketing_crm (localhost:5434)")
        print("   Tabelas:")
        print("     - users (1 registro)")
        print("     - clients (3 registros)")
        print("     - appointments (3 registros)")
        print()
        print("💡 QUERIES ÚTEIS:")
        print("   SELECT * FROM clients;")
        print("   SELECT * FROM appointments;")
        print("   SELECT c.full_name, a.scheduled_at, a.meeting_type")
        print("   FROM appointments a")
        print("   JOIN clients c ON c.id = a.client_id;")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(seed_database())
