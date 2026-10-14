"""Phase 5 tests: rendering + logging (dual-format report, CSVs, run log)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from wabbitry_pairing_optimizer.config import load_config
from wabbitry_pairing_optimizer.load_breeders import load_breeders
from wabbitry_pairing_optimizer.load_litters import load_litters
from wabbitry_pairing_optimizer.logging import get_logger, setup_logging
from wabbitry_pairing_optimizer.render import build_report, write_artifacts
from wabbitry_pairing_optimizer.solve import solve

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA = REPO_ROOT / "data"
TMP = REPO_ROOT / "tests" / "_render_tmp"


@pytest.fixture(scope="module")
def roster():
    return load_breeders(DATA / "breeders.json")


@pytest.fixture(scope="module")
def litters(roster):
    return load_litters(DATA / "litters", known_rabbits={b.name for b in roster})


@pytest.fixture(scope="module")
def config():
    c = load_config(DATA / "config.toml")
    return c.model_copy(
        update={
            "optimization": c.optimization.model_copy(
                update={"seed": 42, "min_runs": 30, "stall_limit": 10}
            )
        }
    )


def _solve_and_report(roster, litters, config):
    from wabbitry_pairing_optimizer import coancestry_matrix_r, doe_production_scores

    sol = solve(
        roster, litters, config, fixed_pairs=[("yaz", "betty"), ("yaz", "lily"), ("yaz", "kiki")]
    )
    mat = coancestry_matrix_r(roster, config.kinship)
    prod = doe_production_scores(roster, litters, config.productivity)
    fixed = [p for p in sol.pairings if p.fixed]
    report = build_report(sol, roster, fixed, mat, prod)
    return sol, report, mat, prod


def test_write_artifacts_all_files(roster, litters, config) -> None:
    """Rendering produces all four artifact files in the output dir."""
    import shutil

    shutil.rmtree(TMP, ignore_errors=True)
    sol, report, mat, prod = _solve_and_report(roster, litters, config)
    out_cfg = config.output
    written = write_artifacts(str(TMP), report, config.optimization.seed, mat, prod, out_cfg)
    paths = [Path(p).name for p in written]
    assert {
        out_cfg.report_json,
        out_cfg.report_md,
        out_cfg.kinship_table_csv,
        out_cfg.doe_productivity_csv,
    } <= set(paths)
    # Output dir created even though it didn't exist before this call.
    assert TMP.is_dir()


def test_json_report_content(roster, litters, config) -> None:
    """The JSON report carries pairings, seed, and the full-solution score."""
    sol, report, mat, prod = _solve_and_report(roster, litters, config)
    write_artifacts(str(TMP), report, 42, mat, prod, config.output)
    doc = json.loads((TMP / config.output.report_json).read_text(encoding="utf-8"))
    assert doc["seed"] == 42
    assert doc["seedless"] is False
    assert len(doc["pairings"]) == len(sol.pairings)
    assert doc["schedule_days"] == sol.schedule_days
    assert "final" in doc["score"]
    # The Yaz fixed pairs are present and scored.
    yaz_pairs = [p for p in doc["pairings"] if p["sire"] == "yaz"]
    assert len(yaz_pairs) == 3


def test_markdown_report_content(roster, litters, config) -> None:
    """The markdown report lists pairings and the score table."""
    sol, report, mat, prod = _solve_and_report(roster, litters, config)
    write_artifacts(str(TMP), report, 42, mat, prod, config.output)
    md = (TMP / config.output.report_md).read_text(encoding="utf-8")
    assert "Wascally Wabbitry" in md
    assert "full-solution score" in md.lower()
    assert "**final**" in md
    # Every dam appears in the pairings list.
    for p in sol.pairings:
        assert p.dam in md


def test_csv_tables(roster, litters, config) -> None:
    """Kinship table + doe productivity CSVs are written with a header."""
    sol, report, mat, prod = _solve_and_report(roster, litters, config)
    write_artifacts(str(TMP), report, 42, mat, prod, config.output)
    kin = (TMP / config.output.kinship_table_csv).read_text(encoding="utf-8")
    prodcsv = (TMP / config.output.doe_productivity_csv).read_text(encoding="utf-8")
    assert kin.startswith("sire,dam,kinship_r")
    assert prodcsv.startswith("doe,productivity_index")
    assert "opal" in prodcsv  # a real doe in the productivity table


def test_logging_to_file(roster, litters, config) -> None:
    """Run logging goes to the log file in the output dir, not stdout."""
    import shutil

    shutil.rmtree(TMP / "logd", ignore_errors=True)
    logger = setup_logging(config.output, str(TMP / "logd"))
    logger.info("test message %d", 7)
    log_path = TMP / "logd" / config.output.log_filename
    assert log_path.exists()
    text = log_path.read_text(encoding="utf-8")
    assert "test message 7" in text
    # get_logger returns the configured logger.
    assert get_logger() is logger


def test_cli_end_to_end(roster, litters, config, capsys) -> None:
    """Running the CLI solves the round, writes artifacts, emits json by default."""
    import shutil

    from wabbitry_pairing_optimizer.__main__ import main

    outdir = TMP / "clid"
    shutil.rmtree(outdir, ignore_errors=True)
    rc = main(
        [
            str(DATA / "breeders.json"),
            "--config",
            str(DATA / "config.toml"),
            "--pairs",
            str(DATA / "fixed_pairs.json"),
            "--seed",
            "7",
            "--output-dir",
            str(outdir),
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    doc = json.loads(out)  # default emission is json
    assert doc["command"] == "solve"
    assert doc["seed"] == 7
    assert doc["unbred_does"] == []
    for name in (
        "wabbitry-report.json",
        "wabbitry-report.md",
        "kinship-table.csv",
        "doe-productivity.csv",
    ):
        assert (outdir / name).exists()
    # Text emission differs from json.
    rc2 = main(
        [
            str(DATA / "breeders.json"),
            "--seed",
            "7",
            "--output",
            "text",
            "--output-dir",
            str(outdir),
        ]
    )
    assert rc2 == 0
    out2 = capsys.readouterr().out
    assert "Breeding round solved" in out2
