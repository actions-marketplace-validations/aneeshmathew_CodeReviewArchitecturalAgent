from code_review_agent.ingestion.ast_parser import ASTParser
from code_review_agent.ingestion.chunker import CodeChunker


def test_ast_parsing_symbols():
    code = """
class DataService:
    def fetch_data(self, url: str) -> dict:
        return {"url": url}

def process_pipeline():
    svc = DataService()
    return svc.fetch_data("https://api.example.com")
"""
    parser = ASTParser()
    symbols = parser.parse_code(code, "test_file.py")

    names = [s.name for s in symbols]
    assert "DataService" in names
    assert "DataService.fetch_data" in names
    assert "process_pipeline" in names

    # Call graph extraction
    graph = parser.build_call_graph(symbols)
    assert isinstance(graph, dict)


def test_code_chunker_logical_units():
    code = """
def func_a():
    return 1

def func_b():
    return 2
"""
    parser = ASTParser()
    chunker = CodeChunker(parser=parser)
    import tempfile
    from pathlib import Path

    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(code)
        path = f.name

    try:
        chunks = chunker.chunk_file(path)
        assert len(chunks) == 2
        chunk_names = [c.name for c in chunks]
        assert "func_a" in chunk_names
        assert "func_b" in chunk_names
    finally:
        Path(path).unlink()
