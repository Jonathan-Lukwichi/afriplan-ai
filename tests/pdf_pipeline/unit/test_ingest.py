"""Tests for PDF stage P1 (ingest)."""

from agent.pdf_pipeline.stages.ingest import ingest


def test_ingest_returns_one_image_per_page(synthetic_pdf_bytes):
    result = ingest(synthetic_pdf_bytes, file_name="test.pdf")
    assert result.page_count_total == 3
    assert len(result.pages_processed) == 3
    for p in result.pages_processed:
        assert p.image_b64                 # not empty
        assert p.image_b64.isascii()
        assert p.width_px > 0
        assert p.height_px > 0


def test_ingest_caps_at_max_pages(synthetic_pdf_bytes):
    result = ingest(synthetic_pdf_bytes, file_name="test.pdf", max_pages=2)
    assert len(result.pages_processed) == 2
    assert result.truncated is True


def test_ingest_hashes_input(synthetic_pdf_bytes):
    a = ingest(synthetic_pdf_bytes)
    b = ingest(synthetic_pdf_bytes)
    assert a.file_sha256 == b.file_sha256
    assert len(a.file_sha256) == 64
