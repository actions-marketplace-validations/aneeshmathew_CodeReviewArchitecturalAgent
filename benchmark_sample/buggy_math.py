import sys  # unused import for Ruff F401 test


def calculate_sum(a: int, b: int) -> int:
    """Calculates sum of two integers."""
    # Bug: subtracts instead of adding, causing test to fail
    return a - b


def multiply_numbers(a: int, b: int) -> int:
    """Multiplies two numbers."""
    return a * b
