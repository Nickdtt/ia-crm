"""
Teste manual SIMPLES - Sistema de bloqueio
Roda rápido e mostra resultados claros
"""

import asyncio
from datetime import date
from app.core.database import AsyncSessionLocal
from app.services.appointmentService import (
    get_available_slots,
    block_full_day,
    block_shift,
    unblock_date
)


async def main():
    print("\n🧪 TESTANDO SISTEMA DE BLOQUEIO\n")
    
    async with AsyncSessionLocal() as db:
        test_date = date(2026, 3, 3)  # Segunda-feira futura
        
        # TESTE 1: Slots normais
        print("1️⃣ Consultando slots disponíveis...")
        slots = await get_available_slots(test_date, db)
        print(f"   Resultado: {len(slots)} slots → {', '.join(slots)}")
        print(f"   ✅ Esperado: 7 slots (9-11h, 14-17h)")
        
        # TESTE 2: Bloquear dia inteiro
        print("\n2️⃣ Bloqueando dia inteiro...")
        await block_full_day(test_date, db)
        slots_blocked = await get_available_slots(test_date, db)
        print(f"   Resultado: {len(slots_blocked)} slots")
        print(f"   ✅ Esperado: 0 slots (dia bloqueado)")
        
        # TESTE 3: Desbloquear
        print("\n3️⃣ Desbloqueando dia...")
        await unblock_date(test_date, db)
        slots_after = await get_available_slots(test_date, db)
        print(f"   Resultado: {len(slots_after)} slots → {', '.join(slots_after)}")
        print(f"   ✅ Esperado: 7 slots (voltou ao normal)")
        
        # TESTE 4: Bloquear só manhã
        print("\n4️⃣ Bloqueando apenas manhã...")
        await block_shift(test_date, "morning", db)
        slots_morning = await get_available_slots(test_date, db)
        print(f"   Resultado: {len(slots_morning)} slots → {', '.join(slots_morning)}")
        print(f"   ✅ Esperado: 4 slots (14-17h) - apenas tarde")
        
        # TESTE 5: Desbloquear e bloquear só tarde
        print("\n5️⃣ Desbloqueando e bloqueando apenas tarde...")
        await unblock_date(test_date, db)
        await block_shift(test_date, "afternoon", db)
        slots_afternoon = await get_available_slots(test_date, db)
        print(f"   Resultado: {len(slots_afternoon)} slots → {', '.join(slots_afternoon)}")
        print(f"   ✅ Esperado: 3 slots (9-11h) - apenas manhã")
        
        # Cleanup final
        print("\n6️⃣ Limpeza final...")
        await unblock_date(test_date, db)
        print("   ✅ Bloqueios removidos")
        
        print("\n✅ TODOS OS TESTES CONCLUÍDOS\n")


if __name__ == "__main__":
    asyncio.run(main())
