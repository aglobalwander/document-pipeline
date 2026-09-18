"""Hermetic checks for the R3 residue read: the normaliser, the family key, and the verdicts.

KM's first pass was wrong because its key was asymmetric, so the key rules are what these pin.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/standards"))

from km_r3_residual_read import exact_key, family_key, normalised, read_row  # noqa: E402


def test_a_label_prefix_is_stripped_but_a_discipline_prefix_survives():
    """`Dance: DA:...` is a KM key defect; `TH: Re7.1.I.` is the paper's own spacing."""
    assert normalised("Dance: DA:Cn10.1.III") == normalised("DA:Cn10.1.III")
    assert normalised("TH: Re7.1.I.") == normalised("TH:Re7.1.I"), (
        "the discipline must survive a printed space after the colon — stripping it was the asymmetry")


def test_a_sub_item_letter_is_stripped_both_attached_and_spaced():
    assert normalised("DA:Re8.1.III a.") == normalised("DA:Re8.1.III")
    assert normalised("MU:Re7.1.3a") == normalised("MU:Re7.1.3")
    # A printed cell can carry the tail twice; stripping one pass leaves the key asymmetric again.
    assert normalised("DA:Re8.1.III a. b.") == normalised("DA:Re8.1.III")


def test_the_family_key_equates_the_notation_variants_a_ruling_would_join():
    assert family_key("TH:Cr2.1.I") == family_key("TH:Cr2-I.")
    assert family_key("TH:Re7.1.-III.") == family_key("TH:Re7.1.III")


def index_of(*codes):
    return {exact_key(c): {"printed_code": c, "documents": "Theatre at a Glance.pdf",
                           "first_page": "5", "first_bbox": "[1, 2, 3, 4]"} for c in codes}


def test_a_printed_code_resolves_exactly():
    out = read_row({"title_or_code": "MU:Cr2.1.1a", "native_uuid": "u"}, index_of("MU:Cr2.1.1a"), [])

    assert out["status"] == "printed" and out["rule"] == "exact"
    assert out["page"] == "5"


def test_a_notation_variant_is_evidence_for_a_ruling_not_a_match():
    out = read_row({"title_or_code": "TH:Cr2.1.I", "native_uuid": "u"}, index_of("TH:Cr2-I."), [])

    assert out["status"] == "near_form"
    assert out["rule"] == "needs_notation_ruling", "a ruling is KM's; this only reports the evidence"
    assert out["printed_form"] == "TH:Cr2-I."


def test_a_derived_strand_prefix_is_not_a_miss():
    out = read_row({"title_or_code": "MU-T:Cn10.0.Ia", "native_uuid": "u"},
                   index_of("MU:Cn10.0.Ia"), [])

    assert out["status"] == "derived_prefix"
    assert "Ruling A" in out["evidence"]


def test_an_absent_code_is_a_named_region_not_a_blank():
    out = read_row({"title_or_code": "TH:Cr1.1.5", "native_uuid": "u"}, index_of("TH:Cr1.1.1"), [])

    assert out["status"] == "no_printed_code"
    assert out["evidence"], "an absent row must say what the family does print"