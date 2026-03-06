from dataclasses import dataclass
import docker
import docker.errors
import requests.exceptions
import tempfile
import os
import shutil
import time
from app.core.config import settings

docker_client = docker.from_env()


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
    tmp_dir = tempfile.mkdtemp()
    
    try:
        with open(os.path.join(tmp_dir, "submission.py"), "w", encoding="utf-8") as f:
            f.write(code)
        
        start = time.time()
        
        try:
            output = docker_client.containers.run(
                image=settings.SANDBOX_IMAGE,
                command="python /code/submission.py",
                volumes={tmp_dir: {"bind": "/code", "mode": "ro"}},
                mem_limit=settings.SANDBOX_MEM_LIMIT,
                nano_cpus=settings.SANDBOX_CPU_QUOTA,
                network_disabled=True,
                read_only=True,
                user="1000",
                privileged=False,
                remove=True,
                stdout=True,
                stderr=True,
                timeout=settings.SANDBOX_TIMEOUT_SECONDS
            )
            elapsed = time.time() - start
            stdout_str = output.decode("utf-8", errors="replace") if output else ""
            return ExecutionResult(
                stdout=stdout_str,
                stderr="",
                traceback="",
                exit_code=0,
                execution_time=elapsed,
                success=True,
                timed_out=False
            )
        except docker.errors.ContainerError as e:
            elapsed = time.time() - start
            stderr_str = e.stderr.decode("utf-8", errors="replace") if e.stderr else ""
            return ExecutionResult(
                stdout="",
                stderr=stderr_str,
                traceback=stderr_str,
                exit_code=e.exit_status,
                execution_time=elapsed,
                success=False,
                timed_out=False
            )
        except requests.exceptions.ReadTimeout:
            elapsed = time.time() - start
            return ExecutionResult(
                stdout="",
                stderr="",
                traceback="",
                exit_code=124,
                execution_time=elapsed,
                success=False,
                timed_out=True
            )
        except docker.errors.APIError as e:
            elapsed = time.time() - start
            return ExecutionResult(
                stdout="",
                stderr=str(e),
                traceback=str(e),
                exit_code=-1,
                execution_time=elapsed,
                success=False,
                timed_out=False
            )
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
