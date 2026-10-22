from app.repositories.databricks_document_search import (
    DatabricksDocumentSearchRepository,
)


def main() -> None:
    repository = DatabricksDocumentSearchRepository(
        endpoint_name="ai-project-assistant-search",
    )

    chunks = repository.search(
        query_text="サイバー攻撃 事業リスク",
        edinet_code="E02367",
        doc_id="S100Y9NX",
        num_results=5,
    )

    for rank, chunk in enumerate(chunks, start=1):
        print()
        print(f"--- Rank {rank} ---")
        print(f"chunk_id: {chunk.chunk_id}")
        print(f"section: {chunk.section}")
        print(f"chunk_index: {chunk.chunk_index}")
        print(f"score: {chunk.score}")
        print(f"content: {chunk.content[:300]}")


if __name__ == "__main__":
    main()