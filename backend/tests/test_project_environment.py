"""Exercise the PowerShell environment wrapper's run-through invocation."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys

import pytest


@pytest.fixture
def environment_wrapper(tmp_path, workspace_root):
    shell = shutil.which("pwsh") or shutil.which("powershell")
    if sys.platform != "win32" or shell is None:
        pytest.skip("the project environment wrapper requires Windows PowerShell")
    scripts = tmp_path / "workspace with spaces" / "scripts"
    scripts.mkdir(parents=True)
    wrapper = scripts / "Enter-ProjectEnvironment.ps1"
    shutil.copyfile(workspace_root / "scripts" / wrapper.name, wrapper)

    def run(*command):
        return subprocess.run(
            [shell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(wrapper), *command],
            capture_output=True, text=True, timeout=15,
        )

    return run


def test_run_through_python_version(environment_wrapper):
    result = environment_wrapper(sys.executable, "--version")
    assert result.returncode == 0, result.stderr
    assert f"Python {sys.version_info.major}.{sys.version_info.minor}" in result.stdout


def test_run_through_preserves_arguments_with_spaces(environment_wrapper, tmp_path):
    program = tmp_path / "argument probe.py"
    program.write_text("import json, sys\nprint(json.dumps(sys.argv[1:]))\n", encoding="utf-8")
    arguments = ["two words", "--literal-option", "path with spaces/file.txt"]
    result = environment_wrapper(
        sys.executable, str(program), *arguments,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout.splitlines()[-1]) == arguments


def test_run_through_preserves_exit_code(environment_wrapper, tmp_path):
    program = tmp_path / "exit probe.py"
    program.write_text("raise SystemExit(7)\n", encoding="utf-8")
    result = environment_wrapper(sys.executable, str(program))
    assert result.returncode == 7, result.stderr


def test_run_through_executable_without_arguments(environment_wrapper, tmp_path):
    executable = tmp_path / "command with spaces.cmd"
    executable.write_text("@echo off\necho no arguments\nexit /b 0\n", encoding="utf-8")
    result = environment_wrapper(str(executable))
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines()[-1] == "no arguments"
