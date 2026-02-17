"""
Seed de dados demo para o portfolio.

Popula o banco Supabase com dados fictícios realistas para que o
recrutador veja o dashboard com conteúdo ao acessar.

Cria:
- 10 clientes de segmentos variados de saúde
- 15 agendamentos (futuros com status variados)
- Usa o usuário demo já existente (mdf.nicolas@gmail.com)

Uso:
    cd backend
    python -m scripts.seed_demo
"""

import asyncio
import os
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from app.core.database import AsyncSessionLocal
from app.models.client import Client, ClientSegment
from app.models.appointment import Appointment, AppointmentStatus
from sqlalchemy import select, func


# Dados dos clientes demo
DEMO_CLIENTS = [
    {
        "first_name": "Roberto",
        "last_name": "Ferreira",
        "phone": "71999001122",
        "email": "roberto@clinicasorriso.com.br",
        "company_name": "Clínica Dental Sorriso",
        "segment": ClientSegment.CLINICA_ODONTOLOGICA,
        "monthly_budget": Decimal("8500.00"),
        "main_marketing_problem": "Não aparece no Google Maps quando pesquisam dentista na região. Perde pacientes para concorrentes com presença digital mais forte.",
        "notes": "Lead qualificado pelo agente IA — alta prioridade",
    },
    {
        "first_name": "Ana",
        "last_name": "Costa",
        "phone": "71988112233",
        "email": "ana@clinicamed.com.br",
        "company_name": "Clínica Médica Saúde Total",
        "segment": ClientSegment.CLINICA_MEDICA,
        "monthly_budget": Decimal("15000.00"),
        "main_marketing_problem": "Investe R$ 5mil/mês em Google Ads mas taxa de conversão de lead em paciente é muito baixa (3%).",
        "notes": "Já investiu em marketing antes, quer resultados mensuráveis",
    },
    {
        "first_name": "Carlos",
        "last_name": "Mendes",
        "phone": "71977223344",
        "email": "carlos@farmavida.com.br",
        "company_name": "FarmaVida Natural",
        "segment": ClientSegment.FARMACIA,
        "monthly_budget": Decimal("12000.00"),
        "main_marketing_problem": "Alto custo de aquisição no Google Ads (R$ 45/lead). E-commerce representa apenas 8% do faturamento.",
        "notes": "Rede com 3 lojas, quer expandir e-commerce",
    },
    {
        "first_name": "Mariana",
        "last_name": "Santos",
        "phone": "71966334455",
        "email": "mariana@psicovida.com.br",
        "company_name": "PsicoVida Terapias",
        "segment": ClientSegment.PSICOLOGO,
        "monthly_budget": Decimal("3500.00"),
        "main_marketing_problem": "Dificuldade em atrair pacientes para terapia online. Concorrência crescente de plataformas como Zenklub.",
        "notes": "Clínica com 4 psicólogos, foco em terapia online",
    },
    {
        "first_name": "Ricardo",
        "last_name": "Oliveira",
        "phone": "71955445566",
        "email": "dr.ricardo@derma.com.br",
        "company_name": None,
        "segment": ClientSegment.MEDICO_AUTONOMO,
        "monthly_budget": Decimal("10000.00"),
        "main_marketing_problem": "Profissional renomado mas zero presença digital. Perde pacientes jovens para concorrentes com Instagram ativo.",
        "notes": "Dermatologista — quer começar no Instagram e Google",
    },
    {
        "first_name": "Fernanda",
        "last_name": "Lima",
        "phone": "71944556677",
        "email": "fernanda@esteticaflor.com.br",
        "company_name": "Estética Flor de Lis",
        "segment": ClientSegment.CLINICA_ESTETICA,
        "monthly_budget": Decimal("6000.00"),
        "main_marketing_problem": "Agenda vazia 3 dias por semana. Depende exclusivamente de indicações boca-a-boca.",
        "notes": "Especializada em harmonização facial e botox",
    },
    {
        "first_name": "Paulo",
        "last_name": "Rodrigues",
        "phone": "71933667788",
        "email": "paulo@labexame.com.br",
        "company_name": "LabExame Diagnósticos",
        "segment": ClientSegment.LABORATORIO,
        "monthly_budget": Decimal("20000.00"),
        "main_marketing_problem": "Precisa aumentar volume de exames. Maioria dos clientes vem por convênio, quer atrair particulares.",
        "notes": "Laboratório grande, 2 unidades em Salvador",
    },
    {
        "first_name": "Juliana",
        "last_name": "Alves",
        "phone": "71922778899",
        "email": "juliana@nutrifit.com.br",
        "company_name": "NutriFit Consultoria",
        "segment": ClientSegment.NUTRICIONISTA,
        "monthly_budget": Decimal("2500.00"),
        "main_marketing_problem": "Começou há 6 meses, tem poucos seguidores e não consegue converter em consultas.",
        "notes": "Orçamento abaixo do mínimo — Plano Essencial pode funcionar",
    },
    {
        "first_name": "Marcos",
        "last_name": "Silva",
        "phone": "71911889900",
        "email": "marcos@fisiototal.com.br",
        "company_name": "FisioTotal Reabilitação",
        "segment": ClientSegment.FISIOTERAPEUTA,
        "monthly_budget": Decimal("4500.00"),
        "main_marketing_problem": "Tem boa reputação offline mas não aparece em buscas online. Site desatualizado desde 2019.",
        "notes": "Quer refazer site + Google Ads para fisioterapia esportiva",
    },
    {
        "first_name": "Camila",
        "last_name": "Nascimento",
        "phone": "71900990011",
        "email": "camila@odontocare.com.br",
        "company_name": "OdontoCare Premium",
        "segment": ClientSegment.CLINICA_ODONTOLOGICA,
        "monthly_budget": Decimal("7000.00"),
        "main_marketing_problem": "Quer lançar serviço de implantes mas não sabe como comunicar o diferencial. Concorrência pesada na região.",
        "notes": "Clínica premium, preço acima da média, foco em qualidade",
    },
]


def _future_dt(days: int, hour: int) -> datetime:
    """Retorna datetime futura (dias a partir de agora, hora fixa)."""
    base = datetime.now(timezone.utc) + timedelta(days=days)
    return base.replace(hour=hour, minute=0, second=0, microsecond=0)


async def seed_demo():
    """Popula o banco com dados demo para portfolio."""

    async with AsyncSessionLocal() as db:
        # Verifica se já tem dados
        count = await db.scalar(select(func.count()).select_from(Client))
        if count and count >= 8:
            print(f"⚠️  Banco já tem {count} clientes. Pulando seed para evitar duplicatas.")
            print("   Para re-seed, delete os dados primeiro:")
            print("   DELETE FROM appointments; DELETE FROM clients;")
            return

        print("=" * 60)
        print("🌱 SEED DE DADOS DEMO PARA PORTFOLIO")
        print("=" * 60)

        # --- Clientes ---
        print("\n📋 Criando 10 clientes...")
        clients = []
        for data in DEMO_CLIENTS:
            client = Client(**data)
            db.add(client)
            clients.append(client)

        await db.flush()  # gera IDs sem commitar

        for c in clients:
            print(f"  ✅ {c.first_name} {c.last_name} — {c.segment.value} — R$ {c.monthly_budget}/mês")

        # --- Agendamentos ---
        print("\n📅 Criando 15 agendamentos...")

        appointments_data = [
            # Futuros - pending (recrutador verá na agenda)
            {"client": 0, "days": 1, "hour": 10, "type": "Diagnóstico inicial", "status": AppointmentStatus.PENDING,
             "notes": "Primeira reunião — focar em SEO local e Google Meu Negócio"},
            {"client": 1, "days": 2, "hour": 14, "type": "Apresentação de proposta", "status": AppointmentStatus.PENDING,
             "notes": "Cliente quer campanha completa: Google Ads + SEO + Redes Sociais"},
            {"client": 4, "days": 3, "hour": 9, "type": "Consultoria Instagram", "status": AppointmentStatus.PENDING,
             "notes": "Dermatologista sem presença digital — criar estratégia do zero"},
            {"client": 5, "days": 3, "hour": 15, "type": "Diagnóstico inicial", "status": AppointmentStatus.PENDING,
             "notes": "Clínica estética com agenda vazia — foco em tráfego pago"},
            {"client": 9, "days": 4, "hour": 11, "type": "Estratégia de implantes", "status": AppointmentStatus.PENDING,
             "notes": "Campanha específica para serviço de implantes dentários"},

            # Futuros - confirmed
            {"client": 2, "days": 5, "hour": 10, "type": "Consultoria Google Ads", "status": AppointmentStatus.CONFIRMED,
             "notes": "Revisar campanhas atuais e otimizar ROAS do e-commerce"},
            {"client": 6, "days": 5, "hour": 14, "type": "Proposta Plano Aceleração", "status": AppointmentStatus.CONFIRMED,
             "notes": "Laboratório grande — proposta de plano completo R$ 10k/mês"},
            {"client": 3, "days": 6, "hour": 16, "type": "Follow-up proposta", "status": AppointmentStatus.CONFIRMED,
             "notes": "Discutir proposta enviada semana passada — Plano Essencial"},

            # Futuros - mais distantes
            {"client": 7, "days": 8, "hour": 10, "type": "Diagnóstico inicial", "status": AppointmentStatus.PENDING,
             "notes": "Nutricionista começando — orçamento apertado, avaliar viabilidade"},
            {"client": 8, "days": 9, "hour": 14, "type": "Auditoria de site", "status": AppointmentStatus.PENDING,
             "notes": "Site desatualizado desde 2019 — levantar requisitos para novo site"},
            {"client": 0, "days": 10, "hour": 15, "type": "Follow-up SEO", "status": AppointmentStatus.CONFIRMED,
             "notes": "Segunda reunião — apresentar plano de ação SEO local"},

            # Completed (passado simulado — inseridos com status direto)
            {"client": 1, "days": 12, "hour": 10, "type": "Reunião de onboarding", "status": AppointmentStatus.COMPLETED,
             "notes": "Onboarding concluído — setup de campanhas iniciado"},
            {"client": 2, "days": 14, "hour": 14, "type": "Diagnóstico inicial", "status": AppointmentStatus.COMPLETED,
             "notes": "Diagnóstico concluído — proposta será enviada esta semana"},

            # Cancelled
            {"client": 7, "days": 15, "hour": 9, "type": "Diagnóstico inicial", "status": AppointmentStatus.CANCELLED,
             "notes": "Cliente cancelou — orçamento não comporta no momento"},
            {"client": 5, "days": 16, "hour": 11, "type": "Follow-up", "status": AppointmentStatus.CANCELLED,
             "notes": "Reagendado para próxima semana"},
        ]

        for apt_data in appointments_data:
            client = clients[apt_data["client"]]
            scheduled = _future_dt(apt_data["days"], apt_data["hour"])

            apt = Appointment(
                client_id=client.id,
                scheduled_at=scheduled,
                duration_minutes=60,
                meeting_type=apt_data["type"],
                status=apt_data["status"],
                notes=apt_data["notes"],
            )

            # Se cancelado, preenche campos de cancelamento
            if apt_data["status"] == AppointmentStatus.CANCELLED:
                apt.cancelled_at = datetime.now(timezone.utc)
                apt.cancellation_reason = apt_data["notes"]

            db.add(apt)

            status_emoji = {
                AppointmentStatus.PENDING: "🟡",
                AppointmentStatus.CONFIRMED: "🟢",
                AppointmentStatus.COMPLETED: "🔵",
                AppointmentStatus.CANCELLED: "🔴",
            }
            emoji = status_emoji.get(apt_data["status"], "⚪")
            print(f"  {emoji} {apt_data['type']} — {client.first_name} {client.last_name} — +{apt_data['days']}d {apt_data['hour']}h — {apt_data['status'].value}")

        await db.commit()

        print("\n" + "=" * 60)
        print("✅ SEED COMPLETO!")
        print("=" * 60)
        print(f"  • 10 clientes criados")
        print(f"  • 15 agendamentos (5 pending, 3 confirmed, 2 completed, 2 cancelled, 3 pending futuro)")
        print(f"\n  Dashboard pronto para demonstração! 🎉")


if __name__ == "__main__":
    asyncio.run(seed_demo())
