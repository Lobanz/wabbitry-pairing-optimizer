"""Result rendering: dual-format (json + markdown) report, supporting CSVs.

Operates on the winning ``Solution`` (Phase 4) and supporting tables, writing
the locked artifact set to ``--output-dir`` (design §8):

- ``wabbitry-report.json`` — the agent-consumable structured record (a
  ``PairingReport`` plus run metadata incl. the active PRNG seed).
- ``wabbitry-report.md`` — the human report of the same data.
- ``kinship-table.csv`` — the r matrix.
- ``doe-productivity.csv`` — the doe productivity index.

Only the WINNING solution's artifacts are emitted (no top-N, no ledger).

Single concern: rendering/persisting the result artifacts.
"""

from __future__ import annotations

import csv
from pathlib import Path

from wabbitry_pairing_optimizer.config import OutputConfig
from wabbitry_pairing_optimizer.models import (
    Breeder,
    Pairing,
    PairingReport,
    Solution,
)

__all__ = ["build_report", "write_artifacts"]


def build_report(
    solution: Solution,
    roster: list[Breeder],
    fixed_pairs: list[Pairing],
    kinship_matrix: dict[tuple[str, str], float],
    doe_productivity: dict[str, float],
) -> PairingReport:
    """Assemble the structured report object for a winning solution.

    Args:
        solution: The winning solution.
        roster: Full roster (self-contained report).
        fixed_pairs: Operator fixed pairs (already scored, included in the
            solution's pairings, echoed here for the report).
        kinship_matrix: r matrix keyed by canonical sorted pair.
        doe_productivity: doe name -> productivity index.

    Returns:
        A ``PairingReport`` capturing the whole round.
    """
    kin = {"|".join(k): v for k, v in sorted(kinship_matrix.items())}
    return PairingReport(
        breeders=roster,
        solution=solution,
        fixed_pairs=fixed_pairs,
        kinship_table=kin,
        doe_productivity=doe_productivity,
    )


def write_artifacts(
    output_dir: str,
    report: PairingReport,
    seed: int,
    kinship_matrix: dict[tuple[str, str], float],
    doe_productivity: dict[str, float],
    out_cfg: OutputConfig,
) -> list[str]:
    """Write all result artifacts to ``output_dir`` (created if missing).

    Args:
        output_dir: Destination directory (CLI override or config default).
        report: The structured report.
        seed: The active PRNG seed (0 = seedless/random).
        kinship_matrix: r matrix (canonical sorted pair -> r).
        doe_productivity: doe name -> index.
        out_cfg: The `[output]` config (filename policy).

    Returns:
        Absolute paths of the files written.
    """
    d = Path(output_dir)
    d.mkdir(parents=True, exist_ok=True)

    written: list[str] = []

    # Structured JSON (agent-consumable): seed + config-relevant + report.
    json_path = d / out_cfg.report_json
    json_doc = {
        "seed": seed,
        "seedless": seed == 0,
        "schedule_days": report.solution.schedule_days,
        "pairability_count": report.solution.pairability_count,
        "score": report.solution.score.model_dump(),
        "pairings": [p.model_dump() for p in report.solution.pairings],
        "unbred_does": report.solution.unbred_does,
        "kinship_table": report.kinship_table,
        "doe_productivity": report.doe_productivity,
    }
    json_path.write_text(_pretty(json_doc), encoding="utf-8")
    written.append(str(json_path))

    # Human markdown report.
    md_path = d / out_cfg.report_md
    md_path.write_text(_render_markdown(report, seed), encoding="utf-8")
    written.append(str(md_path))

    # Kinship matrix CSV.
    kin_rows = [
        {"sire": a, "dam": b, "kinship_r": f"{v:.4f}"}
        for (a, b), v in sorted(kinship_matrix.items())
    ]
    written.append(_write_csv(d / out_cfg.kinship_table_csv, kin_rows))

    # Doe productivity CSV.
    prod_rows = [
        {"doe": name, "productivity_index": f"{v:.4f}"}
        for name, v in sorted(doe_productivity.items())
    ]
    written.append(_write_csv(d / out_cfg.doe_productivity_csv, prod_rows))

    return written


def _write_csv(path: Path, rows: list[dict[str, str]]) -> str:
    with path.open("w", newline="", encoding="utf-8") as fh:
        if not rows:
            return str(path)
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return str(path)


def _pretty(obj: object) -> str:
    import json

    return json.dumps(obj, indent=2, default=str)


def _render_markdown(report: PairingReport, seed: int) -> str:
    sol = report.solution
    sc = sol.score
    lines: list[str] = []
    lines.append("# Wascally Wabbitry — breeding round report")
    lines.append("")
    lines.append(f"- **Seed**: {seed} ({'seedless/random' if seed == 0 else 'deterministic'})")
    lines.append(f"- **Schedule**: {sol.schedule_days} days")
    lines.append(f"- **Pairability**: {sol.pairability_count}")
    lines.append(f"- **Unbred does**: {', '.join(sol.unbred_does) or 'none'}")
    lines.append("")
    lines.append("## Full-solution score")
    lines.append("")
    lines.append("| sum_r | sum_history | unbred | sibling | schedule | pairability | **final** |")
    lines.append("|-|-|-|-|-|-|-|")
    lines.append(
        f"| {sc.sum_r:+.2f} | {sc.sum_history:+.2f} | {sc.unbred_penalty:+.2f} "
        f"| {sc.sibling_penalty:+.2f} | {sc.schedule_penalty:+.2f} "
        f"| {sc.pairability:+.2f} | **{sc.final:+.2f}** |"
    )
    lines.append("")
    lines.append("## Pairings")
    lines.append("")
    for p in sorted(sol.pairings, key=lambda x: (x.dam, x.sire)):
        tag = " *(fixed)*" if p.fixed else ""
        lines.append(
            f"- **{p.dam}** ← **{p.sire}** — {p.pair_type}, r={p.kinship_r:.3f}, "
            f"score {p.final_score:+.3f}{tag}"
        )
    lines.append("")
    return "\n".join(lines) + "\n"
