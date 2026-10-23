from app.services.document_versioning import (
    DocumentVersioningService,
)


def test_same_document_has_same_version() -> None:
    service = DocumentVersioningService()

    first = service.create_version(
        doc_id="S100Y9NX",
        business_overview="ゲーム事業",
        business_risks="サイバー攻撃",
    )

    second = service.create_version(
        doc_id="S100Y9NX",
        business_overview="ゲーム事業",
        business_risks="サイバー攻撃",
    )

    assert first == second


def test_changed_document_has_different_version() -> None:
    service = DocumentVersioningService()

    before = service.create_version(
        doc_id="S100Y9NX",
        business_overview="ゲーム事業",
        business_risks="サイバー攻撃",
    )

    after = service.create_version(
        doc_id="S100Y9NX",
        business_overview="ゲーム事業",
        business_risks=(
            "サイバー攻撃および情報漏えい"
        ),
    )

    assert before != after


def test_none_and_empty_string_have_same_version() -> None:
    service = DocumentVersioningService()

    with_none = service.create_version(
        doc_id="S100Y9NX",
        business_overview=None,
        business_risks=None,
    )

    with_empty_string = service.create_version(
        doc_id="S100Y9NX",
        business_overview="",
        business_risks="",
    )

    assert with_none == with_empty_string