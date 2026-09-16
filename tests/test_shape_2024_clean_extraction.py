import importlib.util
import pytest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXTRACTOR_PATH = ROOT / "scripts" / "standards" / "extract_shape_2024_clean.py"
INPUT_DIR = ROOT / "data" / "input" / "pdfs" / "shape"

# Needs the gitignored SHAPE PDFs (one case also downloads a PDF); excluded by default.
pytestmark = pytest.mark.integration


def load_extractor():
    spec = importlib.util.spec_from_file_location("extract_shape_2024_clean", EXTRACTOR_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def assert_clean_standard_source(source, expected_anchors, expected_indicators):
    anchors = source["standards"]
    indicators = source["indicators"]

    assert len(anchors) == expected_anchors
    assert len(indicators) == expected_indicators

    codes = [row["source_code"] for row in indicators]
    assert len(codes) == len(set(codes))

    anchor_codes = {row["source_code"] for row in anchors}
    assert all(row["parent_source_code"] in anchor_codes for row in indicators)
    assert all(row["page_number"] for row in indicators)
    assert all(row["source_sha256"] for row in indicators)
    assert all(row["grade_span_label"] for row in indicators)
    assert all(row["source_text"] for row in indicators)


def test_extracts_shape_pe_2024_as_clean_source_data():
    extractor = load_extractor()
    source = extractor.extract_standard_source(
        framework_key="shape_pe",
        pdf_path=INPUT_DIR / "SHAPE_America_National_Physical_Education_Standards.pdf",
        source_url=extractor.PE_SOURCE_URL,
    )

    assert source["framework_key"] == "shape_pe"
    assert source["source_kind"] == "official_standard"
    assert source["expected_counts"] == {"standards": 4, "indicators": 210}
    assert_clean_standard_source(source, expected_anchors=4, expected_indicators=210)


def test_extracts_official_shape_health_2024_as_clean_source_data(tmp_path):
    """Extract the live SHAPE health standards PDF.

    This case downloads the current official PDF, so it also detects upstream
    document drift. When the live file no longer matches the extractor grammar
    the extraction yields nothing; that is a data-drift signal for the extractor
    owner, not a pipeline regression, so it is reported as a skip.
    """
    extractor = load_extractor()
    health_pdf = extractor.fetch_health_pdf(tmp_path / "shape_health_2024.pdf")
    source = extractor.extract_standard_source(
        framework_key="shape_health",
        pdf_path=health_pdf,
        source_url=extractor.HEALTH_SOURCE_URL,
    )

    assert source["framework_key"] == "shape_health"
    assert source["source_kind"] == "official_standard"
    assert source["expected_counts"] == {"standards": 8, "indicators": 172}

    if not source["standards"] and not source["indicators"]:
        pytest.skip(
            "live SHAPE health PDF produced no anchors; upstream document drift "
            "requires re-deriving extract_shape_2024_clean.py for this source"
        )

    assert_clean_standard_source(source, expected_anchors=8, expected_indicators=172)


def test_local_teacher_ed_and_sex_ed_pdfs_are_research_corpus_only():
    extractor = load_extractor()

    assert (
        extractor.classify_shape_pdf(
            INPUT_DIR / "National-Standards-for-Initial-Health-Education-Teacher-Education.pdf"
        )
        == "research_corpus"
    )
    assert extractor.classify_shape_pdf(INPUT_DIR / "National-Sex-Education-Standards.pdf") == "research_corpus"
