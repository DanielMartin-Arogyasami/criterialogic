"""ClinicalTrials.gov atom pool: extraction fidelity, provenance, and determinism.

Every test here runs offline against `tests/fixtures/ctgov_cache/` (5 real cached
records). Nothing in this file may make a network request.
"""
import json
import re
from pathlib import Path

import pytest

from criterialogic.data import atom_pool as ap
from criterialogic.data.loaders import ctgov
from criterialogic.schema.logical_form import EntityType, Source
from criterialogic.tasks.compositional import _atom_pool, generate_compositional_items

FIXTURE_CACHE = Path(__file__).parent / "fixtures" / "ctgov_cache"
FETCHED = "2026-01-01T00:00:00+00:00"


def _fixture_studies():
    studies = ctgov.load_cached_studies(FIXTURE_CACHE)
    assert studies, f"fixture cache is empty: {FIXTURE_CACHE}"
    return studies


def _fixture_pool(tmp_path) -> Path:
    records, stats = ctgov.build_atom_records(_fixture_studies(), FETCHED)
    return ap.write_pool(records, stats, {"fixture": True}, tmp_path / "pool.json")


# --------------------------------------------------------------------------- #
# Sentence segmentation
# --------------------------------------------------------------------------- #
def test_sections_bullets_and_escapes():
    text = (
        "Inclusion Criteria:\n\n"
        "* Age 18 to 65 years\n"
        "6\\. History of myocardial infarction\n\n"
        "Exclusion Criteria:\n\n"
        "* Platelet count \\<150\n"
    )
    got = list(ctgov.iter_criterion_sentences(text))
    assert got == [
        ("inclusion", "Age 18 to 65 years"),
        ("inclusion", "History of myocardial infarction"),
        ("exclusion", "Platelet count <150"),
    ]


# --------------------------------------------------------------------------- #
# Extraction fidelity — the rules that keep an atom faithful to its sentence
# --------------------------------------------------------------------------- #
def test_unit_is_read_from_text_not_a_lexicon():
    """Trials report the same analyte in different units; substituting one fabricates it."""
    (atom, _), = [ctgov._sentence_to_atom("Hemoglobin >=80 g/L")]
    assert atom.numeric.value == 80.0
    assert atom.numeric.unit == "g/L"


def test_relative_bound_is_skipped():
    """'<= 3 times ULN' is not an absolute threshold, so no atom may claim it is."""
    assert ctgov._sentence_to_atom("Total bilirubin <=3 times ULN") is None


def test_coordinated_phrase_is_rejected_not_truncated():
    hit = ctgov._sentence_to_atom("Use of any oral or intravenous antibiotics")
    assert hit is None, "a coordinated phrase must not be clipped to its first conjunct"


def test_enumeration_is_rejected():
    hit = ctgov._sentence_to_atom("History of significant cardiac, pulmonary, or renal disease")
    assert hit is None


def test_inline_bound_never_lands_in_entity_text():
    hit = ctgov._sentence_to_atom("Patients with a calculated residual stromal depth <250 um")
    assert hit is None


def test_numeric_constraints_only_on_measurable_entities():
    """Schema invariant: a numeric bound requires measurement/observation/person."""
    records, _ = ctgov.build_atom_records(_fixture_studies(), FETCHED)
    numeric_types = {EntityType.MEASUREMENT, EntityType.OBSERVATION, EntityType.PERSON}
    for r in records:
        if r.atom.numeric is not None:
            assert r.atom.entity.type in numeric_types


def test_age_range_and_minimum():
    atom, pattern = ctgov._sentence_to_atom("Adult patients aged between 18 and 65 years.")
    assert pattern == "age_range"
    assert (atom.numeric.value, atom.numeric.upper, atom.numeric.unit) == (18.0, 65.0, "years")
    atom, pattern = ctgov._sentence_to_atom("Age >=18 years, male or female;")
    assert pattern == "age_min" and atom.numeric.value == 18.0


# --------------------------------------------------------------------------- #
# Provenance — every atom resolves back to real trial text
# --------------------------------------------------------------------------- #
def test_every_atom_resolves_to_its_source_sentence():
    records, _ = ctgov.build_atom_records(_fixture_studies(), FETCHED)
    assert records
    by_nct = {ctgov.nct_id(s): ctgov.eligibility_text(s) for s in _fixture_studies()}
    for r in records:
        assert r.nct_id in by_nct
        source = re.sub(r"\s+", " ", ctgov._ESCAPE_RE.sub(r"\1", by_nct[r.nct_id]))
        assert r.sentence in source, f"{r.sentence!r} not found verbatim in {r.nct_id}"
        assert r.first_posted, "posting date is what backs the contamination claim"


def test_generated_item_carries_resolvable_nct_ids(tmp_path):
    pool_path = _fixture_pool(tmp_path)
    pool = ap.load_ctgov_pool(pool_path)
    items = generate_compositional_items(n_per_depth=4, max_depth=3, seed=29, pool=pool)
    assert items
    texts = {ctgov.nct_id(s): ctgov.eligibility_text(s) for s in _fixture_studies()}
    for item in items:
        assert item.criterion.source is Source.CTGOV
        assert item.criterion.metadata["atom_source"] == ap.CTGOV
        assert item.criterion.metadata["composition"] == "synthetic"
        ncts = item.criterion.metadata["source_nct_ids"].split(",")
        assert ncts and all(n in texts for n in ncts)
    # ... and the trail runs all the way back to the sentence.
    atom = items[0].criterion.expression
    while not hasattr(atom, "entity"):
        atom = getattr(atom, "operand", None) or atom.operands[0]
    prov = pool.provenance_for(atom)
    assert prov and prov.sentence
    source = re.sub(r"\s+", " ", ctgov._ESCAPE_RE.sub(r"\1", texts[prov.nct_id]))
    assert prov.sentence in source


# --------------------------------------------------------------------------- #
# Determinism
# --------------------------------------------------------------------------- #
def test_pool_build_is_byte_identical_across_runs(tmp_path):
    a = _fixture_pool(tmp_path / "a")
    b = _fixture_pool(tmp_path / "b")
    assert a.read_bytes() == b.read_bytes()


def test_generation_is_byte_identical_for_same_seed_and_pool(tmp_path):
    pool = ap.load_ctgov_pool(_fixture_pool(tmp_path))
    first = [i.model_dump_json() for i in generate_compositional_items(4, 3, 29, pool=pool)]
    second = [i.model_dump_json() for i in generate_compositional_items(4, 3, 29, pool=pool)]
    assert first == second


def test_pool_digest_is_recorded_on_items(tmp_path):
    pool = ap.load_ctgov_pool(_fixture_pool(tmp_path))
    items = generate_compositional_items(2, 2, 29, pool=pool)
    assert {i.criterion.metadata["atom_pool_sha256"] for i in items} == {pool.sha256}


# --------------------------------------------------------------------------- #
# Failing loudly — no silent fallback to any other atom source
# --------------------------------------------------------------------------- #
def test_missing_pool_raises_with_build_instructions(tmp_path):
    with pytest.raises(ap.AtomPoolUnavailable) as e:
        ap.load_ctgov_pool(tmp_path / "absent.json")
    msg = str(e.value)
    assert "scripts/fetch_ctgov_snapshot.py" in msg
    assert str(tmp_path / "absent.json") in msg


def test_atom_pool_does_not_fall_back(tmp_path):
    with pytest.raises(ap.AtomPoolUnavailable):
        _atom_pool(ap.CTGOV, tmp_path / "absent.json")


def test_empty_pool_is_an_error(tmp_path):
    p = tmp_path / "empty.json"
    p.write_text(json.dumps({"atoms": []}), encoding="utf-8")
    with pytest.raises(ap.AtomPoolUnavailable):
        ap.load_ctgov_pool(p)


def test_unknown_atom_source_rejected():
    with pytest.raises(ValueError):
        ap.load_pool("wishful_thinking")


# --------------------------------------------------------------------------- #
# Acquisition mechanics (no network)
# --------------------------------------------------------------------------- #
def test_query_records_the_sampling_frame():
    q = ctgov.StudyQuery(first_posted_from="2026-01-01")
    expr = q.advanced_expression()
    assert "AREA[Phase]PHASE4" in expr
    assert "AREA[StudyType]INTERVENTIONAL" in expr
    assert "AREA[StudyFirstPostDate]RANGE[2026-01-01,MAX]" in expr
    assert q.as_params()["filter.advanced"] == expr


def test_rate_limiter_spaces_requests():
    now = [0.0]
    slept: list[float] = []

    def sleep(s):
        slept.append(s)
        now[0] += s

    limiter = ctgov.RateLimiter(interval=0.5, clock=lambda: now[0], sleep=sleep)
    limiter.wait()          # first call is free
    limiter.wait()          # immediately after: must sleep the full interval
    now[0] += 2.0
    limiter.wait()          # long gap: no sleep needed
    assert slept == [0.5]


def test_cache_hit_is_never_refetched(monkeypatch):
    def explode(*a, **k):
        raise AssertionError("cache hit must not trigger an HTTP request")

    monkeypatch.setattr(ctgov, "_http_json", explode)
    nct = ctgov.nct_id(_fixture_studies()[0])
    out = ctgov.fetch_eligibility([nct], cache_dir=FIXTURE_CACHE)
    assert out[nct]


def test_fixture_manifest_records_the_query():
    manifest = ctgov.read_manifest(FIXTURE_CACHE)
    assert manifest and manifest["api_base"] == ctgov.API_BASE
    assert manifest["rate_limit_requests_per_second"] <= 2.0
