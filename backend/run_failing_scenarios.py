"""
run_failing_scenarios.py

Roda apenas os cenários 16, 17 e 20 que falharam anteriormente.
"""

import asyncio
import sys
from pathlib import Path

backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

# Importar tudo do simulate_all_flows
from simulate_all_flows import (
    cleanup_phones,
    scenario_16,
    scenario_17,
    scenario_20,
    results,
    print_final_report,
    PHONES,
)
from app.core.database import AsyncSessionLocal
from sqlalchemy import text


async def cleanup_selected():
    """Limpa apenas os telefones dos cenários 16, 17 e 20."""
    async with AsyncSessionLocal() as db:
        for num in [16, 17, 20]:
            phone = PHONES[num]
            await db.execute(text(
                f"DELETE FROM appointments WHERE client_id IN (SELECT id FROM clients WHERE phone = '{phone}')"
            ))
            await db.execute(text(f"DELETE FROM clients WHERE phone = '{phone}'"))
        await db.commit()


async def main():
    print("\n🎯 Rodando apenas os cenários 16, 17 e 20...\n")

    print("🧹 Limpando dados dos cenários 16, 17 e 20...")
    await cleanup_selected()
    print("✅ Limpo\n")

    for fn in [scenario_16, scenario_17, scenario_20]:
        try:
            await fn()
        except Exception as e:
            import traceback
            print(f"\n❌ ERRO: {e}")
            traceback.print_exc()
        await asyncio.sleep(0.5)

    print_final_report()


if __name__ == "__main__":
    asyncio.run(main())
