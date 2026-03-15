"""
run_compare.py

Roda simulate_all_flows.py duas vezes:
  1. Com o grafo ORIGINAL  (graph.py)
  2. Com o grafo COM GUARD (graph_with_guard.py)

Compara os resultados cenário a cenário e exibe um resumo lado a lado.

Uso:
    python run_compare.py
"""

import asyncio
import subprocess
import sys
import re
from pathlib import Path

BACKEND = Path(__file__).parent
VENV_PYTHON = BACKEND / "venv" / "bin" / "python"
SIMULATE = BACKEND / "simulate_all_flows.py"

# --------------------------------------------------------------------------- #
# Helpers                                                                       #
# --------------------------------------------------------------------------- #

def run_simulation(graph_env: str) -> tuple[str, int]:
    """Executa simulate_all_flows.py com a variável GRAPH_MODE definida."""
    env = {"GRAPH_MODE": graph_env}
    import os
    full_env = {**os.environ, **env}
    result = subprocess.run(
        [str(VENV_PYTHON), str(SIMULATE)],
        capture_output=True,
        text=True,
        cwd=str(BACKEND),
        env=full_env,
    )
    return result.stdout + result.stderr, result.returncode


def parse_results(output: str) -> dict[int, dict]:
    """
    Extrai pass/fail de cada cenário a partir da saída do simulate_all_flows.
    Procura padrões como:
      ✅ Cenário 1  ...
      ❌ Cenário 1  ...
    """
    scenarios = {}
    for line in output.splitlines():
        m = re.search(r"(✅|❌)\s+Cenário\s+(\d+)[:\s]*(.*)", line)
        if m:
            icon, num, rest = m.group(1), int(m.group(2)), m.group(3).strip()
            scenarios[num] = {
                "passed": icon == "✅",
                "label": rest,
                "icon": icon,
            }
    return scenarios


def extract_summary_line(output: str) -> str:
    """Extrai a linha de resumo final (ex: '20/20 passaram')."""
    for line in reversed(output.splitlines()):
        if "TOTAL:" in line or ("passaram" in line and "cenários" in line.lower()):
            clean = re.sub(r'\x1b\[[0-9;]*m', '', line).strip()
            if clean:
                return clean
    return "(sem resumo)"


# --------------------------------------------------------------------------- #
# Main                                                                          #
# --------------------------------------------------------------------------- #

def main():
    print("=" * 70)
    print("  COMPARAÇÃO DE GRAFOS — simulate_all_flows.py")
    print("=" * 70)

    # ── Limpa banco antes da Rodada 1 ────────────────────────────────────── #
    print("\n🧹 Limpando banco antes de iniciar...")
    run_simulation("cleanup")
    print("   Banco limpo.\n")

    # ── Rodada 1: grafo original ─────────────────────────────────────────── #
    print("\n▶  Rodando com GRAFO ORIGINAL (graph.py) ...")
    print("   (aguarde, pode demorar alguns minutos)\n")
    out_original, rc_original = run_simulation("original")
    results_original = parse_results(out_original)
    summary_original = extract_summary_line(out_original)
    print(out_original)

    # ── Limpa banco entre as rodadas ────────────────────────────────────── #
    print("\n🧹 Limpando banco entre as rodadas...")
    run_simulation("cleanup")
    print("   Banco limpo.\n")

    # ── Rodada 2: grafo com guard ─────────────────────────────────────────── #
    print("\n" + "=" * 70)
    print("\n▶  Rodando com GRAFO COM GUARD (graph_with_guard.py) ...")
    print("   (aguarde, pode demorar alguns minutos)\n")
    out_guard, rc_guard = run_simulation("guard")
    results_guard = parse_results(out_guard)
    summary_guard = extract_summary_line(out_guard)
    print(out_guard)

    # ── Tabela comparativa ──────────────────────────────────────────────────#
    print("\n" + "=" * 70)
    print("  RESULTADO COMPARATIVO")
    print("=" * 70)
    print(f"{'Cenário':<12} {'Original':<14} {'Com Guard':<14} {'Diferença'}")
    print("-" * 60)

    all_nums = sorted(set(results_original) | set(results_guard))
    diffs = []

    for n in all_nums:
        orig = results_original.get(n)
        guard = results_guard.get(n)

        orig_icon  = orig["icon"]  if orig  else "❓"
        guard_icon = guard["icon"] if guard else "❓"
        orig_label = orig["label"] if orig else "não encontrado"

        if orig_icon == guard_icon:
            diff = "  —  igual"
        elif orig_icon == "✅" and guard_icon == "❌":
            diff = "  ⚠️  REGREDIU no guard"
            diffs.append(n)
        elif orig_icon == "❌" and guard_icon == "✅":
            diff = "  🆕 MELHOROU no guard"
            diffs.append(n)
        else:
            diff = "  ❓ dados incompletos"

        print(f"  {n:<10} {orig_icon:<13} {guard_icon:<13} {diff}")

    print("-" * 60)
    print(f"\n  Original  → {summary_original}")
    print(f"  Com Guard → {summary_guard}")

    if diffs:
        print(f"\n  Cenários com diferença: {diffs}")
    else:
        print("\n  ✅ Nenhuma diferença encontrada entre os grafos.")

    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
