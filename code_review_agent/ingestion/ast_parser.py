import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from tree_sitter import Language, Parser
import tree_sitter_python


@dataclass
class CodeSymbol:
    """Represents an extracted code symbol (function, method, class, or module)."""
    name: str
    kind: str  # 'function' | 'method' | 'class' | 'module'
    file_path: str
    start_line: int
    end_line: int
    docstring: Optional[str] = None
    parameters: List[str] = field(default_factory=list)
    return_type: Optional[str] = None
    calls: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    raw_code: str = ""


class ASTParser:
    """Extracts symbols, functions, classes, and call graphs using Tree-Sitter and Python AST."""

    def __init__(self):
        py_language = Language(tree_sitter_python.language())
        self.parser = Parser(py_language)

    def parse_code(self, code_str: str, file_path: str = "") -> List[CodeSymbol]:
        """Parses a code string into symbols using Tree-sitter, falling back to Python AST if needed."""
        try:
            return self._parse_with_tree_sitter(code_str, file_path)
        except Exception:
            # Safe fallback to standard library ast
            return self._parse_with_python_ast(code_str, file_path)

    def parse_file(self, file_path: str | Path) -> List[CodeSymbol]:
        """Reads and parses a file from disk."""
        path = Path(file_path)
        if not path.is_file() or not path.suffix == ".py":
            return []
        try:
            content = path.read_text(encoding="utf-8")
            return self.parse_code(content, str(path))
        except Exception:
            return []

    def _parse_with_tree_sitter(self, code_str: str, file_path: str) -> List[CodeSymbol]:
        """Extracts symbols via Tree-Sitter AST traversal."""
        code_bytes = code_str.encode("utf-8")
        tree = self.parser.parse(code_bytes)
        root = tree.root_node
        symbols: List[CodeSymbol] = []
        lines = code_str.splitlines()

        def get_node_text(node) -> str:
            return code_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")

        def extract_calls(node) -> List[str]:
            calls = []
            def visit_call(n):
                if n.type == "call":
                    func_node = n.child_by_field_name("function")
                    if func_node:
                        calls.append(get_node_text(func_node))
                for child in n.children:
                    visit_call(child)
            visit_call(node)
            return list(set(calls))

        def traverse(node, current_class: Optional[str] = None):
            if node.type == "class_definition":
                name_node = node.child_by_field_name("name")
                class_name = get_node_text(name_node) if name_node else "AnonymousClass"
                start_line = node.start_point[0] + 1
                end_line = node.end_point[0] + 1
                raw_code = "\n".join(lines[start_line - 1:end_line])

                symbols.append(CodeSymbol(
                    name=class_name,
                    kind="class",
                    file_path=file_path,
                    start_line=start_line,
                    end_line=end_line,
                    raw_code=raw_code
                ))

                body_node = node.child_by_field_name("body")
                if body_node:
                    for child in body_node.children:
                        traverse(child, current_class=class_name)
                return

            if node.type == "function_definition":
                name_node = node.child_by_field_name("name")
                fn_name = get_node_text(name_node) if name_node else "anonymous_func"
                start_line = node.start_point[0] + 1
                end_line = node.end_point[0] + 1
                raw_code = "\n".join(lines[start_line - 1:end_line])
                
                # Parameters
                params_node = node.child_by_field_name("parameters")
                params = []
                if params_node:
                    for child in params_node.children:
                        if child.type in ("identifier", "typed_parameter", "default_parameter"):
                            params.append(get_node_text(child))

                # Return type
                ret_node = node.child_by_field_name("return_type")
                return_type = get_node_text(ret_node) if ret_node else None

                # Function calls inside
                calls = extract_calls(node)

                full_name = f"{current_class}.{fn_name}" if current_class else fn_name
                symbols.append(CodeSymbol(
                    name=full_name,
                    kind="method" if current_class else "function",
                    file_path=file_path,
                    start_line=start_line,
                    end_line=end_line,
                    parameters=params,
                    return_type=return_type,
                    calls=calls,
                    raw_code=raw_code
                ))
                return

            for child in node.children:
                traverse(child, current_class)

        traverse(root)
        return symbols

    def _parse_with_python_ast(self, code_str: str, file_path: str) -> List[CodeSymbol]:
        """Fallback parser using Python's built-in ast module."""
        symbols: List[CodeSymbol] = []
        try:
            tree = ast.parse(code_str)
        except Exception:
            return symbols

        lines = code_str.splitlines()

        class ASTVisitor(ast.NodeVisitor):
            def __init__(self):
                self.current_class: Optional[str] = None

            def visit_ClassDef(self, node: ast.ClassDef):
                start = node.lineno
                end = getattr(node, "end_lineno", start)
                raw_code = "\n".join(lines[start - 1:end])
                doc = ast.get_docstring(node)

                symbols.append(CodeSymbol(
                    name=node.name,
                    kind="class",
                    file_path=file_path,
                    start_line=start,
                    end_line=end,
                    docstring=doc,
                    raw_code=raw_code
                ))

                old_class = self.current_class
                self.current_class = node.name
                self.generic_visit(node)
                self.current_class = old_class

            def visit_FunctionDef(self, node: ast.FunctionDef):
                self._handle_func(node)

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
                self._handle_func(node)

            def _handle_func(self, node: ast.FunctionDef | ast.AsyncFunctionDef):
                start = node.lineno
                end = getattr(node, "end_lineno", start)
                raw_code = "\n".join(lines[start - 1:end])
                doc = ast.get_docstring(node)
                params = [arg.arg for arg in node.args.args]
                calls = [
                    call.func.id if isinstance(call.func, ast.Name)
                    else (call.func.attr if isinstance(call.func, ast.Attribute) else "complex_call")
                    for call in ast.walk(node) if isinstance(call, ast.Call)
                ]

                full_name = f"{self.current_class}.{node.name}" if self.current_class else node.name
                symbols.append(CodeSymbol(
                    name=full_name,
                    kind="method" if self.current_class else "function",
                    file_path=file_path,
                    start_line=start,
                    end_line=end,
                    docstring=doc,
                    parameters=params,
                    calls=list(set(calls)),
                    raw_code=raw_code
                ))

        visitor = ASTVisitor()
        visitor.visit(tree)
        return symbols

    def build_call_graph(self, symbols: List[CodeSymbol]) -> Dict[str, List[str]]:
        """Constructs an inverted and forward call graph across all symbols."""
        graph: Dict[str, List[str]] = {}
        symbol_names: Set[str] = {s.name for s in symbols}

        for symbol in symbols:
            graph[symbol.name] = [call for call in symbol.calls if any(call in name for name in symbol_names)]
        return graph
