from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
from .ast_parser import ASTParser, CodeSymbol


@dataclass
class CodeChunk:
    """A logical unit of code (function, class, or module preamble)."""
    chunk_id: str
    file_path: str
    name: str
    kind: str  # 'function' | 'method' | 'class' | 'module_preamble'
    start_line: int
    end_line: int
    code: str
    metadata: Dict[str, str] = field(default_factory=dict)


class CodeChunker:
    """Chunks source code by logical units rather than fixed token count."""

    def __init__(self, parser: Optional[ASTParser] = None):
        self.parser = parser or ASTParser()

    def chunk_file(self, file_path: str | Path) -> List[CodeChunk]:
        """Chunks a single file into logical units."""
        path = Path(file_path)
        if not path.is_file() or path.suffix != ".py":
            return []

        try:
            content = path.read_text(encoding="utf-8")
        except Exception:
            return []

        symbols = self.parser.parse_code(content, str(path))
        lines = content.splitlines()
        chunks: List[CodeChunk] = []

        if not symbols:
            # If no symbols extracted, chunk entire file
            chunks.append(CodeChunk(
                chunk_id=f"{path.name}:1-{len(lines)}",
                file_path=str(path),
                name=path.name,
                kind="file",
                start_line=1,
                end_line=len(lines),
                code=content,
                metadata={"file": str(path)}
            ))
            return chunks

        # Add logical chunks for symbols
        for symbol in symbols:
            chunk_id = f"{path.name}:{symbol.name}:{symbol.start_line}-{symbol.end_line}"
            chunks.append(CodeChunk(
                chunk_id=chunk_id,
                file_path=str(path),
                name=symbol.name,
                kind=symbol.kind,
                start_line=symbol.start_line,
                end_line=symbol.end_line,
                code=symbol.raw_code,
                metadata={
                    "file": str(path),
                    "symbol_name": symbol.name,
                    "kind": symbol.kind,
                    "calls": ",".join(symbol.calls),
                    "parameters": ",".join(symbol.parameters),
                }
            ))

        return chunks

    def chunk_directory(self, dir_path: str | Path, exclude_dirs: Optional[List[str]] = None) -> List[CodeChunk]:
        """Recursively chunks all Python files in a directory."""
        path = Path(dir_path)
        exclude = set(exclude_dirs or [".venv", "venv", ".git", "__pycache__", "node_modules", ".pytest_cache", ".ruff_cache", ".mypy_cache"])
        all_chunks: List[CodeChunk] = []

        for py_file in path.rglob("*.py"):
            # Check exclusions
            parts = set(py_file.parts)
            if parts.intersection(exclude):
                continue
            all_chunks.extend(self.chunk_file(py_file))

        return all_chunks
