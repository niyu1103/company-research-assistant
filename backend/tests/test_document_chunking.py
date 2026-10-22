import pytest

from app.services.document_chunking import DocumentChunkingService


def test_chunk_text_returns_empty_for_none() -> None:
    service = DocumentChunkingService()

    chunks = service.chunk_text(
        doc_id="S100TEST",
        edinet_code="E00000",
        section="business_risks",
        text=None,
    )

    assert chunks == []


def test_chunk_text_returns_empty_for_blank_text() -> None:
    service = DocumentChunkingService()

    chunks = service.chunk_text(
        doc_id="S100TEST",
        edinet_code="E00000",
        section="business_risks",
        text="   ",
    )

    assert chunks == []


def test_chunk_text_creates_overlapping_chunks() -> None:
    service = DocumentChunkingService()

    chunks = service.chunk_text(
        doc_id="S100TEST",
        edinet_code="E00000",
        section="business_risks",
        text="ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        chunk_size=10,
        overlap=3,
    )

    assert len(chunks) == 4

    assert chunks[0].content == "ABCDEFGHIJ"
    assert chunks[1].content == "HIJKLMNOPQ"
    assert chunks[2].content == "OPQRSTUVWX"
    assert chunks[3].content == "VWXYZ"

    assert chunks[0].content[-3:] == chunks[1].content[:3]
    assert chunks[1].content[-3:] == chunks[2].content[:3]
    assert chunks[2].content[-3:] == chunks[3].content[:3]


def test_chunk_text_sets_chunk_metadata() -> None:
    service = DocumentChunkingService()

    chunks = service.chunk_text(
        doc_id="S100X6X6",
        edinet_code="E03217",
        section="business_risks",
        text="ABCDEFGHIJKLMNO",
        chunk_size=10,
        overlap=2,
    )

    assert chunks[0].chunk_id == "S100X6X6_business_risks_0"
    assert chunks[0].doc_id == "S100X6X6"
    assert chunks[0].edinet_code == "E03217"
    assert chunks[0].section == "business_risks"
    assert chunks[0].chunk_index == 0

    assert chunks[1].chunk_id == "S100X6X6_business_risks_1"
    assert chunks[1].chunk_index == 1


@pytest.mark.parametrize(
    ("chunk_size", "overlap"),
    [
        (0, 0),
        (-1, 0),
        (10, -1),
        (10, 10),
        (10, 11),
    ],
)
def test_chunk_text_rejects_invalid_chunk_settings(
    chunk_size: int,
    overlap: int,
) -> None:
    service = DocumentChunkingService()

    with pytest.raises(ValueError):
        service.chunk_text(
            doc_id="S100TEST",
            edinet_code="E00000",
            section="business_risks",
            text="test text",
            chunk_size=chunk_size,
            overlap=overlap,
        )