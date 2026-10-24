"""Command-line interface for the pairing optimizer.

Phase 0 establishes the CLI **emission convention** (design §8), not the full
CLI. Per the two-layer model:

- **Layer 1 — ``--output json|text``** governs ALL terminal emissions: help,
  version, errors, status. ``json`` emits every message as a structure an agent
  can consume; ``text`` is human-readable. ``--output`` is **NOT a config
  parameter** (it only governs the stdout interface).
- **Layer 2 — the result content** is always written dual-format to
  ``--output-dir`` (json + markdown). That rendering lands with the solver in
  Phase 4/5 (``solve.py`` / ``render.py``).

This module currently wires the emission convention and the argument contract.
Full solver wiring and output-dir rendering are implemented in later phases.
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from typing import TextIO

from wabbitry_pairing_optimizer.config import ConfigError
from wabbitry_pairing_optimizer.load_breeders import BreedersError
from wabbitry_pairing_optimizer.load_litters import LittersError
from wabbitry_pairing_optimizer.recipe import RecipeError

__all__ = ["main"]


def _version() -> str:
    """Return the package version (static in pyproject; no VCS plugin needed)."""
    return "0.1.0"


def _emit_json(obj: object) -> str:
    return json.dumps(obj, indent=2)


def _emit(emission: str, obj: object, stream: TextIO | None = None) -> None:
    # Resolve stdout at call time (not import time) so test capture and
    # stdout redirection see the current stream.
    out = sys.stdout if stream is None else stream
    if emission == "json":
        out.write(_emit_json(obj) + "\n")
    else:
        # obj is a plain string/bytes-like message for text mode.
        out.write(f"{obj}\n")


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns a process exit code.

    ``--output`` is read from argv up front so help/error/version emission can
    honor it. Solver + rendering are wired in later phases.
    """
    parser = argparse.ArgumentParser(
        prog="wabbitry-pairing-optimizer",
        description="Least-bad breeding pairings for Wascally Wabbitry.",
        add_help=False,
    )
    parser.add_argument(
        "breeders",
        nargs="?",
        default="data/breeders.json",
        help="path to breeders.json (default data/breeders.json)",
    )
    parser.add_argument(
        "--pairs", metavar="FILE", help="pre-decided pairings JSON (list of Pairing)"
    )
    parser.add_argument("--config", metavar="FILE", default="data/config.toml")
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="override PRNG seed (0 = random); positive fixes it for reproducibility",
    )
    parser.add_argument(
        "--output",
        choices=("json", "text"),
        default="json",
        help="program emission format: json (agent) or text (human); default json",
    )
    parser.add_argument("--output-dir", metavar="DIR", help="result artifact output directory")
    parser.add_argument("-h", "--help", action="store_true", help="show help and exit")
    parser.add_argument("--version", action="store_true", help="show version and exit")

    pre, _ = parser.parse_known_args(argv)
    emission: str = getattr(pre, "output", "json")

    if getattr(pre, "help", False):
        _emit(emission, parser.format_help())
        return 0
    if getattr(pre, "version", False):
        _emit(
            emission,
            {
                "command": "version",
                "package": "wabbitry-pairing-optimizer",
                "version": _version(),
            }
            if emission == "json"
            else f"wabbitry-pairing-optimizer {_version()}",
        )
        return 0

    # --- Run the full round (solver + render). ---
    try:
        import json as _json
        from pathlib import Path

        from wabbitry_pairing_optimizer import (
            coancestry_matrix_r,
            doe_production_scores,
            load_breeders,
            load_config,
            load_litters,
        )
        from wabbitry_pairing_optimizer.logging import get_logger, setup_logging
        from wabbitry_pairing_optimizer.render import build_report, write_artifacts
        from wabbitry_pairing_optimizer.schedule import build_schedule
        from wabbitry_pairing_optimizer.solve import solve

        cfg = load_config(getattr(pre, "config", "data/config.toml"))
        # CLI --seed overrides the config value (precedence: CLI -> config).
        cli_seed = getattr(pre, "seed", None)
        if cli_seed is not None:
            cfg = cfg.model_copy(
                update={"optimization": cfg.optimization.model_copy(update={"seed": cli_seed})}
            )
        breeders = load_breeders(getattr(pre, "breeders", "data/breeders.json"))
        litters_dir = str(Path(getattr(pre, "breeders", "data/breeders.json")).parent / "litters")
        litters = load_litters(litters_dir, known_rabbits={b.name for b in breeders})

        # Fixed pairs from --pairs (list of {"sire","dam"}).
        fixed_pairs: list[tuple[str, str]] = []
        pairs_file = getattr(pre, "pairs", None)
        if pairs_file:
            with open(pairs_file, encoding="utf-8") as fh:
                for entry in _json.load(fh):
                    fixed_pairs.append((entry["sire"], entry["dam"]))

        # Resolve the output directory (CLI overrides config default) + log.
        output_dir = getattr(pre, "output_dir", None) or cfg.output.output_dir
        setup_logging(cfg.output, output_dir)

        solution = solve(breeders, litters, cfg, fixed_pairs=fixed_pairs)
        mat = coancestry_matrix_r(breeders, cfg.kinship)
        prod = doe_production_scores(breeders, litters, cfg.productivity)
        fixed_pairings = [p for p in solution.pairings if p.fixed]
        report = build_report(solution, breeders, fixed_pairings, mat, prod)
        max_bucks = cfg.optimization.buck_batch_capacity
        written = write_artifacts(
            output_dir,
            report,
            cfg.optimization.seed,
            mat,
            prod,
            cfg.output,
            max_bucks_per_day=max_bucks,
        )

        # Day-batch calendars (both modes) for the JSON consumer.
        def _cal(mode: int) -> dict[str, list[str]]:
            return {
                f"Day {d}": [f"{p.sire} x {p.dam}" for p in ps]
                for d, ps in sorted(build_schedule(solution.pairings, mode).items())
            }

        _emit(
            emission,
            {
                "command": "solve",
                "output_dir": output_dir,
                "artifacts": written,
                "seed": cfg.optimization.seed,
                "schedule_days": solution.schedule_days,
                "pairability_count": solution.pairability_count,
                "unbred_does": solution.unbred_does,
                "final_score": solution.score.final,
                "n_pairings": len(solution.pairings),
                "schedule_capped_at": max_bucks,
                "schedule_capped": _cal(max_bucks),
                "schedule_all_bucks": _cal(0),
            }
            if emission == "json"
            else (
                f"Breeding round solved: {len(solution.pairings)} pairings, "
                f"final score {solution.score.final:+.2f}, "
                f"{solution.schedule_days} days, unbred={solution.unbred_does or 'none'}.\n"
                f"Artifacts written to {output_dir}/"
            ),
        )
        logger = get_logger()
        logger.info(
            "solved round: seed=%d pairings=%d final=%.2f days=%d",
            cfg.optimization.seed,
            len(solution.pairings),
            solution.score.final,
            solution.schedule_days,
        )
        return 0
    except (
        ConfigError,
        BreedersError,
        LittersError,
        RecipeError,
        OSError,
        ValueError,
        KeyError,
        TypeError,
    ) as exc:
        # Expected failure modes (bad config, missing/broken data files): a
        # clean, concise error for both emission modes.
        _emit(emission, {"command": "error", "error": str(exc)})
        return 1
    except Exception as exc:  # noqa: BLE001 - unexpected; surface the root cause
        # Anything else is unexpected — hide nothing. Include the exception
        # type + traceback so the operator sees what actually went wrong.
        if emission == "json":
            _emit(
                emission,
                {
                    "command": "error",
                    "error": str(exc),
                    "type": type(exc).__name__,
                    "unexpected": True,
                    "traceback": traceback.format_exc(),
                },
            )
        else:
            _emit(
                emission,
                f"unexpected error ({type(exc).__name__}): {exc}\n{traceback.format_exc()}",
            )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
