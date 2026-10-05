from code_review_agent.ingestion.chunker import CodeChunk
from code_review_agent.ingestion.vector_store import CodeVectorStore


def test_code_vector_store_in_memory_fallback():
    store = CodeVectorStore(index_name="test-index", pinecone_api_key=None)

    chunks = [
        CodeChunk(
            chunk_id="chunk1",
            file_path="math_utils.py",
            name="add_numbers",
            kind="function",
            start_line=1,
            end_line=5,
            code="def add_numbers(a: int, b: int) -> int:\n    return a + b\n",
            metadata={"docstring": "Add two integers"}
        ),
        CodeChunk(
            chunk_id="chunk2",
            file_path="string_utils.py",
            name="reverse_string",
            kind="function",
            start_line=1,
            end_line=4,
            code="def reverse_string(s: str) -> str:\n    return s[::-1]\n",
            metadata={"docstring": "Reverse a string"}
        ),
    ]

    indexed_count = store.index_chunks(chunks)
    assert indexed_count == 2

    # Query for addition / math
    results = store.search_similar_code("add numbers integer addition", limit=2)
    assert len(results) > 0
    assert results[0]["payload"]["name"] == "add_numbers"
