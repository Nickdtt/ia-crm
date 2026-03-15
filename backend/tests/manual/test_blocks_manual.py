"""
Script de teste manual para funções de bloqueio de agendamentos.

Executa testes sequenciais e mostra resultados no terminal.

Uso:
    python test_blocks_manual.py
"""

import asyncio
from datetime import date, datetime, time
from app.core.database import AsyncSessionLocal
from app.services.appointmentService import (
    get_available_slots,
    block_full_day,
    block_shift,
    unblock_date
)


async def test_1_available_slots_normal():
    """Teste 1: Buscar slots disponíveis em dia normal (sem bloqueios)"""
    print("\n🧪 TESTE 1: Slots disponíveis - dia normal")
    print("-" * 50)
    
    async with AsyncSessionLocal() as db:
        target = date(2026, 2, 3)  # Segunda-feira
        slots = await get_available_slots(target, db)
        
        expected = 7  # 3 manhã + 4 tarde
        assert len(slots) == expected, f"❌ Esperado {expected} slots, obteve {len(slots)}"
        assert "09:00" in slots, "❌ 09:00 deveria estar disponível"
        assert "12:00" not in slots, "❌ 12:00 NÃO deveria estar (almoço)"
        assert "13:00" not in slots, "❌ 13:00 NÃO deveria estar (almoço)"
        assert "14:00" in slots, "❌ 14:00 deveria estar disponível"
        
        print(f"✅ PASSOU - {len(slots)} slots disponíveis")
        print(f"   Slots: {slots}")


async def test_2_weekend_closed():
    """Teste 2: Fim de semana retorna lista vazia"""
    print("\n🧪 TESTE 2: Fim de semana fechado")
    print("-" * 50)
    
    async with AsyncSessionLocal() as db:
        saturday = date(2026, 1, 31)
        sunday = date(2026, 2, 1)
        
        slots_sat = await get_available_slots(saturday, db)
        slots_sun = await get_available_slots(sunday, db)
        
        assert len(slots_sat) == 0, f"❌ Sábado deveria estar fechado, mas tem {len(slots_sat)} slots"
        assert len(slots_sun) == 0, f"❌ Domingo deveria estar fechado, mas tem {len(slots_sun)} slots"
        
        print("✅ PASSOU - Fim de semana corretamente fechado")


async def test_3_block_full_day():
    """Teste 3: Bloquear dia inteiro"""
    print("\n🧪 TESTE 3: Bloquear dia inteiro")
    print("-" * 50)
    
    async with AsyncSessionLocal() as db:
        target = date(2026, 2, 4)  # Terça-feira
        
        # Antes do bloqueio
        slots_before = await get_available_slots(target, db)
        print(f"   Antes: {len(slots_before)} slots disponíveis")
        
        # Bloquear
        await block_full_day(target, db)
        print(f"   🔒 Bloqueio aplicado")
        
        # Depois do bloqueio
        slots_after = await get_available_slots(target, db)
        print(f"   Depois: {len(slots_after)} slots disponíveis")
        
        assert len(slots_after) == 0, f"❌ Dia bloqueado deveria ter 0 slots, mas tem {len(slots_after)}"
        
        print("✅ PASSOU - Dia completamente bloqueado")
        
        # Limpar bloqueio para não afetar outros testes
        await unblock_date(target, db)


async def test_4_block_morning():
    """Teste 4: Bloquear apenas manhã"""
    print("\n🧪 TESTE 4: Bloquear turno da manhã")
    print("-" * 50)
    
    async with AsyncSessionLocal() as db:
        target = date(2026, 2, 5)  # Quarta-feira
        
        # Bloquear manhã
        await block_shift(target, "morning", db)
        print(f"   🔒 Manhã bloqueada")
        
        # Verificar slots
        slots = await get_available_slots(target, db)
        
        assert "09:00" not in slots, "❌ 09:00 deveria estar bloqueado"
        assert "10:00" not in slots, "❌ 10:00 deveria estar bloqueado"
        assert "11:00" not in slots, "❌ 11:00 deveria estar bloqueado"
        assert "14:00" in slots, "❌ 14:00 deveria estar disponível (tarde)"
        assert "15:00" in slots, "❌ 15:00 deveria estar disponível (tarde)"
        
        print(f"✅ PASSOU - Manhã bloqueada, tarde disponível")
        print(f"   Slots disponíveis: {slots}")
        
        # Limpar
        await unblock_date(target, db)


async def test_5_block_afternoon():
    """Teste 5: Bloquear apenas tarde"""
    print("\n🧪 TESTE 5: Bloquear turno da tarde")
    print("-" * 50)
    
    async with AsyncSessionLocal() as db:
        target = date(2026, 2, 6)  # Quinta-feira
        
        # Bloquear tarde
        await block_shift(target, "afternoon", db)
        print(f"   🔒 Tarde bloqueada")
        
        # Verificar slots
        slots = await get_available_slots(target, db)
        
        assert "09:00" in slots, "❌ 09:00 deveria estar disponível (manhã)"
        assert "10:00" in slots, "❌ 10:00 deveria estar disponível (manhã)"
        assert "14:00" not in slots, "❌ 14:00 deveria estar bloqueado"
        assert "15:00" not in slots, "❌ 15:00 deveria estar bloqueado"
        assert "16:00" not in slots, "❌ 16:00 deveria estar bloqueado"
        
        print(f"✅ PASSOU - Tarde bloqueada, manhã disponível")
        print(f"   Slots disponíveis: {slots}")
        
        # Limpar
        await unblock_date(target, db)


async def test_6_unblock():
    """Teste 6: Desbloquear data"""
    print("\n🧪 TESTE 6: Desbloquear data")
    print("-" * 50)
    
    async with AsyncSessionLocal() as db:
        target = date(2026, 2, 7)  # Sexta-feira
        
        # Bloquear dia inteiro
        await block_full_day(target, db)
        slots_blocked = await get_available_slots(target, db)
        print(f"   Bloqueado: {len(slots_blocked)} slots")
        assert len(slots_blocked) == 0, "❌ Deveria estar bloqueado"
        
        # Desbloquear
        await unblock_date(target, db)
        print(f"   🔓 Desbloqueio aplicado")
        
        # Verificar se voltou ao normal
        slots_unblocked = await get_available_slots(target, db)
        print(f"   Desbloqueado: {len(slots_unblocked)} slots")
        
        assert len(slots_unblocked) == 7, f"❌ Deveria ter 7 slots, mas tem {len(slots_unblocked)}"
        
        print("✅ PASSOU - Data desbloqueada com sucesso")


async def run_all_tests():
    """Executa todos os testes sequencialmente"""
    print("=" * 50)
    print("🚀 INICIANDO TESTES DE BLOQUEIO DE AGENDAMENTOS")
    print("=" * 50)
    
    tests = [
        test_1_available_slots_normal,
        test_2_weekend_closed,
        test_3_block_full_day,
        test_4_block_morning,
        test_5_block_afternoon,
        test_6_unblock
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            await test()
            passed += 1
        except AssertionError as e:
            failed += 1
            print(f"\n❌ FALHOU: {e}")
        except Exception as e:
            failed += 1
            print(f"\n💥 ERRO INESPERADO: {e}")
    
    print("\n" + "=" * 50)
    print("📊 RESULTADO FINAL")
    print("=" * 50)
    print(f"✅ Passou: {passed}/{len(tests)}")
    print(f"❌ Falhou: {failed}/{len(tests)}")
    
    if failed == 0:
        print("\n🎉 TODOS OS TESTES PASSARAM!")
    else:
        print(f"\n⚠️  {failed} teste(s) falharam")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
