"""Issue #28 tests: ad-hoc query rows + ranked best-for-x (query module + CLI)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from wabbitry_pairing_optimizer.config import load_config
from wabbitry_pairing_optimizer.load_breeders import load_breeders
from wabbitry_pairing_optimizer.load_litters import load_litters
from wabbitry_pairing_optimizer.query import (
    load_fixed_pairs,
    parse_pair_spec,
    query_pairs,
    rank_for_subject,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA = REPO_ROOT / "data"


@pytest.fixture(scope="module")
def roster():
    return load_breeders(DATA / "breeders.json")


@pytest.fixture(scope="module")
def litters(roster):
    return load_litters(DATA / "litters", known_rabbits={b.name for b in roster})


@pytest.fixture(scope="module")
def config():
    return load_config(DATA / "config.toml")


@pytest.fixture(scope="module")
def fixed_pairs():
    return load_fixed_pairs(str(DATA / "fixed_pairs.json"))


def _row(rows, sire, dam):
    return next(r for r in rows if r.sire == sire and r.dam == dam)


def test_query_full_metric_row(roster, litters, config) -> None:
    """uno x abby carries the complete payload (r, kind, tier, breakdown)."""
    rows = query_pairs([("uno", "abby")], roster, litters, config)
    assert len(rows) == 1
    r = rows[0]
    assert r.sire == "uno" and r.dam == "abby"
    assert r.sire_breed == "M70 NZW" and r.dam_breed == "M70 NZW"
    assert r.strain == "M70"
    assert r.kinship_r == pytest.approx(0.5)
    assert r.related_pct == 50.0
    assert r.relationship_kind == "full_sib"
    assert r.tier == "sibling"
    assert r.tier_penalty == 5.0
    assert r.doe_productivity == pytest.approx(4.1)
    assert r.final_score == pytest.approx(-1.4)
    assert r.fixed is False
    assert r.cross_strain is False
    assert r.warnings == ["full-sibling"]
    # Productivity detail exposes the components behind the index. abby has no
    # own litters (her index blends from dam abigail), so the components pin the
    # thin-record path: own_count 0, consistency 0.
    d = r.doe_productivity_detail
    assert d.index == pytest.approx(4.1)
    assert d.own_litter_count == 0
    assert d.consistency == 0.0
    assert 0.0 <= d.w_own <= 1.0


def test_query_parent_offspring(roster, litters, config) -> None:
    """uno x opal is parent-offspring line-breeding, same score as zack x opal."""
    rows = query_pairs([("uno", "opal")], roster, litters, config)
    r = rows[0]
    assert r.kinship_r == pytest.approx(0.4375)
    assert r.relationship_kind == "parent_offspring"
    assert r.tier == "line_bred"
    assert r.warnings == ["parent-offspring"]
    assert r.final_score == pytest.approx(3.3625)
    # Opal has her own litter history (one 6-kit litter).
    assert r.doe_productivity_detail.own_litter_count == 1


def test_query_outcross(roster, litters, config) -> None:
    """yaz x abby is a true outcross: r 0, no warnings, best score."""
    rows = query_pairs([("yaz", "abby")], roster, litters, config)
    r = rows[0]
    assert r.kinship_r == 0.0
    assert r.tier == "outcross"
    assert r.warnings == []
    assert r.final_score == pytest.approx(4.1)


def test_query_cross_strain_flagged(roster, litters, config) -> None:
    """M70 x TAMUK pair is flagged cross_strain (pools are never crossed)."""
    rows = query_pairs([("uno", "fiona")], roster, litters, config)
    assert rows[0].cross_strain is True


def test_query_unknown_name_raises(roster, litters, config) -> None:
    with pytest.raises(ValueError, match="unknown"):
        query_pairs([("no-such-buck", "abby")], roster, litters, config)


def test_parse_pair_spec() -> None:
    assert parse_pair_spec("yaz:abby, uno:opal") == [("yaz", "abby"), ("uno", "opal")]
    assert parse_pair_spec("  yaz:abby , uno:opal  ") == [("yaz", "abby"), ("uno", "opal")]


def test_parse_pair_spec_bad() -> None:
    with pytest.raises(ValueError, match="missing ':'"):
        parse_pair_spec("yazabby")
    with pytest.raises(ValueError, match="empty"):
        parse_pair_spec("yaz:")


def test_load_fixed_pairs_inline_and_file(fixed_pairs) -> None:
    assert load_fixed_pairs("yaz:abby") == [("yaz", "abby")]
    assert len(fixed_pairs) == 3  # yaz -> betty/lily/kiki from the committed file
    with pytest.raises(ValueError, match="not a file"):
        load_fixed_pairs("yaz zzz")


def test_rank_buck_uno_same_strain(roster, litters, config) -> None:
    """Best does for uno: same-strain only, score order, opal on top."""
    rows = rank_for_subject("uno", "buck", roster, litters, config)
    assert all(r.strain == "M70" for r in rows)
    assert len(rows) == 7  # M70 does: abby/amber/betty/kiki/lily/maxine/opal
    assert rows[0].dam == "opal"  # highest final_score (3.3625)
    finals = [r.final_score for r in rows]
    assert finals == sorted(finals, reverse=True)


def test_rank_doe_opal_order(roster, litters, config) -> None:
    """Best bucks for opal: yaz outcross first; uno/zack tie broken by name."""
    rows = rank_for_subject("opal", "doe", roster, litters, config)
    assert [r.sire for r in rows] == ["yaz", "uno", "zack"]
    assert rows[0].kinship_r == 0.0


def test_rank_sort_r(roster, litters, config) -> None:
    """--sort r orders least-related first."""
    rows = rank_for_subject("opal", "doe", roster, litters, config, sort="r")
    rs = [r.kinship_r for r in rows]
    assert rs == sorted(rs)
    assert rows[0].sire == "yaz"


def test_rank_all_strains(roster, litters, config) -> None:
    """--all-strains includes TAMUK does for an M70 buck (flagged cross-strain)."""
    rows = rank_for_subject("uno", "buck", roster, litters, config, all_strains=True)
    breeds = {r.dam_breed for r in rows}
    assert "TAMUK NZW" in breeds  # TAMUK does present (13 total: 7 M70 + 6 TAMUK)
    assert any(r.cross_strain for r in rows)
    assert len(rows) == 13


def test_rank_fixed_rows_flagged(roster, litters, config, fixed_pairs) -> None:
    """Fixed-pair rows are shown and flagged, not filtered out."""
    rows = rank_for_subject("yaz", "buck", roster, litters, config, fixed_pairs)
    fixed = {r.dam for r in rows if r.fixed}
    assert fixed == {"betty", "kiki", "lily"}


def test_cli_query_json(capsys) -> None:
    """CLI --query emits structured rows and does NOT solve."""
    from wabbitry_pairing_optimizer.__main__ import main

    rc = main(
        [
            str(DATA / "breeders.json"),
            "--query",
            "uno:abby, uno:opal",
            "--config",
            str(DATA / "config.toml"),
        ]
    )
    assert rc == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["command"] == "query"
    assert doc["n"] == 2
    assert [r["dam"] for r in doc["rows"]] == ["abby", "opal"]
    assert "doe_productivity_detail" in doc["rows"][0]
    assert doc["rows"][0]["kinship_r"] == pytest.approx(0.5)


def test_cli_rank_json_text(capsys) -> None:
    """CLI --rank emits ranked rows; text mode is human-readable."""
    from wabbitry_pairing_optimizer.__main__ import main

    rc = main(
        [
            str(DATA / "breeders.json"),
            "--rank",
            "doe:opal",
            "--limit",
            "2",
            "--config",
            str(DATA / "config.toml"),
        ]
    )
    assert rc == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["command"] == "rank"
    assert doc["n"] == 2
    assert [r["sire"] for r in doc["rows"]] == ["yaz", "uno"]

    rc2 = main(
        [
            str(DATA / "breeders.json"),
            "--rank",
            "buck:uno",
            "--output",
            "text",
            "--config",
            str(DATA / "config.toml"),
        ]
    )
    assert rc2 == 0
    out = capsys.readouterr().out
    assert "rank" in out
    assert "Uno x Opal" in out


def test_cli_query_inline_pairs_flag(capsys) -> None:
    """Inline fixed-pair spec works for --pairs (no file needed)."""
    from wabbitry_pairing_optimizer.__main__ import main

    rc = main(
        [
            str(DATA / "breeders.json"),
            "--pairs",
            "yaz:abby",
            "--rank",
            "buck:yaz",
            "--config",
            str(DATA / "config.toml"),
        ]
    )
    assert rc == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["command"] == "rank"
    by_dam = {r["dam"]: r for r in doc["rows"]}
    assert by_dam["abby"]["fixed"] is True  # the inline override marked it fixed
    assert by_dam["betty"]["fixed"] is False  # committed default NOT used
