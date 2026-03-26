from dataclasses import dataclass
import io
import json
import os
import tarfile
import time

import docker
import docker.errors
import requests.exceptions

try:
    import httpx as _httpx
    _HTTPX_TIMEOUT: type = _httpx.ReadTimeout
except ImportError:
    _HTTPX_TIMEOUT = None  # type: ignore[assignment]

from app.core.config import settings

# ---------------------------------------------------------------------------
# Pre-execution deny wrapper
#
# This Python snippet is prepended to every user submission before it is
# placed in the container. It overrides the subprocess/os.system/os.popen
# entry-points at the Python level as a defence-in-depth measure on top of
# the seccomp profile. Even if a syscall somehow slips through, the Python
# layer will raise a RuntimeError before any shell command is attempted.
# ---------------------------------------------------------------------------
_DENY_WRAPPER = """\
import builtins as _b, os as _os, sys as _sys

def _blocked(*a, **kw):
    raise RuntimeError(
        "Policy violation: process spawning and shell access are not permitted "
        "in this sandbox. Remove calls to subprocess, os.system, os.popen, "
        "os.exec*, or eval/exec of shell strings."
    )

# Block subprocess module
import importlib, types
_fake_subprocess = types.ModuleType("subprocess")
for _attr in ("run","call","check_call","check_output","Popen","getoutput","getstatusoutput"):
    setattr(_fake_subprocess, _attr, _blocked)
_sys.modules["subprocess"] = _fake_subprocess

# Block os-level spawn/exec helpers
for _fn in ("system","popen","execv","execve","execvp","execvpe",
            "spawnl","spawnle","spawnlp","spawnlpe",
            "spawnv","spawnve","spawnvp","spawnvpe","startfile"):
    if hasattr(_os, _fn):
        setattr(_os, _fn, _blocked)

del _b, _os, _sys, _blocked, _fake_subprocess, _fn, importlib, types
# --- user submission begins below ---
"""

docker_client = None


def get_docker_client():
    global docker_client
    if docker_client is None:
        docker_url = os.environ.get("SANDBOX_DOCKER_URL", "")
        tls_ca = os.environ.get("SANDBOX_DOCKER_TLS_CA", "")
        tls_cert = os.environ.get("SANDBOX_DOCKER_TLS_CERT", "")
        tls_key = os.environ.get("SANDBOX_DOCKER_TLS_KEY", "")
        if docker_url and tls_ca and tls_cert and tls_key:
            tls_config = docker.tls.TLSConfig(
                ca_cert=tls_ca,
                client_cert=(tls_cert, tls_key),
                verify=False,  # cert has no SAN for 'docker-sandbox'; mTLS still enforced
            )
            docker_client = docker.DockerClient(base_url=docker_url, tls=tls_config)
        elif docker_url:
            docker_client = docker.DockerClient(base_url=docker_url)
        else:
            docker_client = docker.from_env()
    return docker_client


def _reset_docker_client():
    """Reset the singleton so the next call to get_docker_client() reconnects."""
    global docker_client
    docker_client = None


def _build_security_opts() -> list[str]:
    """
    Return the security_opt list for the sandbox container.
    Applies the seccomp profile when SANDBOX_SECCOMP_PROFILE is set and the
    file exists; otherwise falls back to no-new-privileges only (dev mode).
    """
    opts = ["no-new-privileges:true"]
    profile_path = settings.SANDBOX_SECCOMP_PROFILE
    if profile_path and os.path.isfile(profile_path):
        opts.append(f"seccomp={profile_path}")
    return opts


@dataclass
class ExecutionResult:
    stdout: str
    stderr: str
    traceback: str
    exit_code: int
    execution_time: float
    success: bool
    timed_out: bool


def execute_code(code: str) -> ExecutionResult:
    start = time.time()

    # Prepend the deny wrapper so Python-level spawn attempts are blocked
    # before the seccomp layer even gets a chance to act.
    hardened_code = _DENY_WRAPPER + code

    try:
        client = get_docker_client()

        # Build tar archive containing the hardened submission
        tar_stream = io.BytesIO()
        with tarfile.open(fileobj=tar_stream, mode='w') as tar:
            code_bytes = hardened_code.encode('utf-8')
            tarinfo = tarfile.TarInfo(name='submission.py')
            tarinfo.size = len(code_bytes)
            tarinfo.mode = 0o644
            tar.addfile(tarinfo, io.BytesIO(code_bytes))
        tar_stream.seek(0)

        container = client.containers.create(
            image=settings.SANDBOX_IMAGE,
            command='python /tmp/submission.py',
            mem_limit=settings.SANDBOX_MEM_LIMIT,
            nano_cpus=settings.SANDBOX_CPU_QUOTA,
            network_disabled=True,
            read_only=True,
            tmpfs={'/tmp': 'size=16m,noexec'},
            security_opt=_build_security_opts(),
            cap_drop=['ALL'],
            user='nobody',
            detach=True,
        )

        try:
            container.put_archive('/tmp', tar_stream)
            container.start()

            # Support both requests (docker-py <6) and httpx (docker-py >=6) backends.
            _timeout_exc = (requests.exceptions.ReadTimeout,)
            if _HTTPX_TIMEOUT is not None:
                _timeout_exc = _timeout_exc + (_HTTPX_TIMEOUT,)

            timed_out = False
            try:
                result = container.wait(timeout=settings.SANDBOX_TIMEOUT_SECONDS)
                exit_code = result.get('StatusCode', 0)
            except _timeout_exc:
                container.kill()
                timed_out = True
                exit_code = 124

            elapsed = time.time() - start

            if timed_out:
                return ExecutionResult(
                    stdout='', stderr='', traceback='',
                    exit_code=exit_code, execution_time=elapsed,
                    success=False, timed_out=True,
                )

            stdout_bytes = container.logs(stdout=True, stderr=False)
            stderr_bytes = container.logs(stdout=False, stderr=True)
            stdout_str = stdout_bytes.decode('utf-8', errors='replace') if stdout_bytes else ''
            stderr_str = stderr_bytes.decode('utf-8', errors='replace') if stderr_bytes else ''

            if exit_code == 0:
                return ExecutionResult(
                    stdout=stdout_str, stderr='', traceback='',
                    exit_code=0, execution_time=elapsed,
                    success=True, timed_out=False,
                )
            else:
                return ExecutionResult(
                    stdout=stdout_str, stderr=stderr_str, traceback=stderr_str,
                    exit_code=exit_code, execution_time=elapsed,
                    success=False, timed_out=False,
                )
        finally:
            try:
                container.remove(force=True)
            except Exception:
                pass

    except docker.errors.ContainerError as e:
        elapsed = time.time() - start
        stderr_str = e.stderr.decode('utf-8', errors='replace') if e.stderr else ''
        return ExecutionResult(
            stdout='', stderr=stderr_str, traceback=stderr_str,
            exit_code=e.exit_status, execution_time=elapsed,
            success=False, timed_out=False,
        )
    except docker.errors.DockerException as e:
        _reset_docker_client()
        elapsed = time.time() - start
        return ExecutionResult(
            stdout='', stderr=str(e), traceback=str(e),
            exit_code=-1, execution_time=elapsed,
            success=False, timed_out=False,
        )
    except Exception as e:
        elapsed = time.time() - start
        return ExecutionResult(
            stdout='', stderr=str(e), traceback=str(e),
            exit_code=-1, execution_time=elapsed,
            success=False, timed_out=False,
        )
