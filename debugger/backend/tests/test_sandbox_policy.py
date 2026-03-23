"""
Tests for the sandbox execution policy.

These tests verify that the deny wrapper prepended to every submission
blocks process-spawning and shell-access vectors before the seccomp layer
acts, and that normal Python code still executes correctly.
"""
import pytest
from app.execution.service import execute_code, _DENY_WRAPPER


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def run(code: str):
    return execute_code(code)


# ---------------------------------------------------------------------------
# Policy: subprocess is blocked
# ---------------------------------------------------------------------------

def test_subprocess_run_is_blocked():
    result = run("import subprocess; subprocess.run(['ls'])")
    assert not result.success
    assert "Policy violation" in result.stderr or "Policy violation" in result.traceback


def test_subprocess_popen_is_blocked():
    result = run("import subprocess; subprocess.Popen(['ls'])")
    assert not result.success
    assert "Policy violation" in result.stderr or "Policy violation" in result.traceback


def test_subprocess_check_output_is_blocked():
    result = run("import subprocess; subprocess.check_output(['echo', 'hi'])")
    assert not result.success
    assert "Policy violation" in result.stderr or "Policy violation" in result.traceback


# ---------------------------------------------------------------------------
# Policy: os.system / os.popen are blocked
# ---------------------------------------------------------------------------

def test_os_system_is_blocked():
    result = run("import os; os.system('ls')")
    assert not result.success
    assert "Policy violation" in result.stderr or "Policy violation" in result.traceback


def test_os_popen_is_blocked():
    result = run("import os; os.popen('ls')")
    assert not result.success
    assert "Policy violation" in result.stderr or "Policy violation" in result.traceback


def test_os_execv_is_blocked():
    result = run("import os; os.execv('/bin/ls', ['ls'])")
    assert not result.success
    assert "Policy violation" in result.stderr or "Policy violation" in result.traceback


# ---------------------------------------------------------------------------
# Policy: normal Python code is unaffected
# ---------------------------------------------------------------------------

def test_print_hello_world_succeeds():
    result = run("print('hello world')")
    assert result.success
    assert "hello world" in result.stdout


def test_arithmetic_succeeds():
    result = run("print(2 + 2)")
    assert result.success
    assert "4" in result.stdout


def test_list_operations_succeed():
    result = run("x = [1, 2, 3]; print(sum(x))")
    assert result.success
    assert "6" in result.stdout


def test_import_math_succeeds():
    result = run("import math; print(math.floor(3.7))")
    assert result.success
    assert "3" in result.stdout


def test_import_json_succeeds():
    result = run("import json; print(json.dumps({'a': 1}))")
    assert result.success
    assert '"a"' in result.stdout


# ---------------------------------------------------------------------------
# Deny wrapper unit test (no Docker required)
# ---------------------------------------------------------------------------

def test_deny_wrapper_blocks_subprocess_at_python_level():
    """Verify the wrapper raises RuntimeError without needing a container."""
    import sys
    # Snapshot sys.modules before exec so we can restore it afterwards,
    # preventing the fake subprocess module from leaking into later tests.
    _saved = sys.modules.copy()
    try:
        namespace: dict = {}
        exec(_DENY_WRAPPER, namespace)  # noqa: S102
        fake = sys.modules.get("subprocess")
        assert fake is not None
        try:
            fake.run(["ls"])
            assert False, "Expected RuntimeError"
        except RuntimeError as e:
            assert "Policy violation" in str(e)
    finally:
        sys.modules.clear()
        sys.modules.update(_saved)
