"""Sandbox execution engine supporting subprocess isolation and Docker containers."""
from .executor import ExecutionResult, SandboxExecutor

__all__ = ["ExecutionResult", "SandboxExecutor"]
