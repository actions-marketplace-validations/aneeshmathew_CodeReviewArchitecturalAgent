from code_review_agent.analyzer.error_parser import ErrorParser


def test_parse_ruff_output():
    json_output = """[
        {
            "code": "F401",
            "filename": "sample.py",
            "location": {"row": 1, "column": 8},
            "message": "`os` imported but unused"
        }
    ]"""
    errors = ErrorParser.parse_ruff(json_output)
    assert len(errors) == 1
    assert errors[0].source_tool == "ruff"
    assert errors[0].error_code == "F401"
    assert errors[0].line_number == 1
    assert errors[0].message == "`os` imported but unused"


def test_parse_mypy_output():
    mypy_output = "service/auth.py:42:5: error: Argument 1 to \"verify\" has incompatible type \"int\"; expected \"str\"  [arg-type]"
    errors = ErrorParser.parse_mypy(mypy_output)
    assert len(errors) == 1
    assert errors[0].source_tool == "mypy"
    assert errors[0].line_number == 42
    assert errors[0].column_number == 5
    assert errors[0].error_code == "arg-type"


def test_parse_pytest_output():
    pytest_output = """
============================= FAILURES =============================
____________________________ test_add _____________________________
FAILED tests/test_calc.py::test_add - AssertionError: assert 5 == 6
"""
    errors = ErrorParser.parse_pytest(pytest_output)
    assert len(errors) >= 1
    assert errors[0].source_tool == "pytest"
    assert "test_add" in errors[0].message
