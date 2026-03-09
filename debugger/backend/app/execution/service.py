from dataclasses import dataclass
import docker
import docker.errors
import requests.exceptions
import tarfile
import io
import tempfile
import os
import shutil
import time
from app.core.config import settings

docker_client = None

def get_docker_client():
    global docker_client
    if docker_client is None:
        docker_client = docker.from_env()
    return docker_client


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
    
    try:
        client = get_docker_client()
        
        # Create tar archive with the code
        tar_stream = io.BytesIO()
        tar = tarfile.open(fileobj=tar_stream, mode='w')
        code_bytes = code.encode('utf-8')
        tarinfo = tarfile.TarInfo(name='submission.py')
        tarinfo.size = len(code_bytes)
        tarinfo.mode = 0o644
        tar.addfile(tarinfo, io.BytesIO(code_bytes))
        tar.close()
        tar_stream.seek(0)
        
        # Create and start container
        container = client.containers.create(
            image=settings.SANDBOX_IMAGE,
            command='python /tmp/submission.py',
            mem_limit=settings.SANDBOX_MEM_LIMIT,
            nano_cpus=settings.SANDBOX_CPU_QUOTA,
            network_disabled=True,
            detach=True
        )
        
        # Copy code into container
        container.put_archive('/tmp', tar_stream)
        
        # Start container
        container.start()
        
        try:
            result = container.wait(timeout=settings.SANDBOX_TIMEOUT_SECONDS)
            logs = container.logs(stdout=True, stderr=True)
            container.remove(force=True)
            elapsed = time.time() - start
            exit_code = result.get('StatusCode', 0)
            
            if exit_code == 0:
                stdout_str = logs.decode('utf-8', errors='replace') if logs else ''
                return ExecutionResult(
                    stdout=stdout_str,
                    stderr='',
                    traceback='',
                    exit_code=0,
                    execution_time=elapsed,
                    success=True,
                    timed_out=False
                )
            else:
                stderr_str = logs.decode('utf-8', errors='replace') if logs else ''
                return ExecutionResult(
                    stdout='',
                    stderr=stderr_str,
                    traceback=stderr_str,
                    exit_code=exit_code,
                    execution_time=elapsed,
                    success=False,
                    timed_out=False
                )
        except requests.exceptions.ReadTimeout:
            container.kill()
            container.remove(force=True)
            elapsed = time.time() - start
            return ExecutionResult(
                stdout='',
                stderr='',
                traceback='',
                exit_code=124,
                execution_time=elapsed,
                success=False,
                timed_out=True
            )
    except docker.errors.ContainerError as e:
        elapsed = time.time() - start
        stderr_str = e.stderr.decode('utf-8', errors='replace') if e.stderr else ''
        return ExecutionResult(
            stdout='',
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
            stdout='',
            stderr='',
            traceback='',
            exit_code=124,
            execution_time=elapsed,
            success=False,
            timed_out=True
        )
    except Exception as e:
        elapsed = time.time() - start
        return ExecutionResult(
            stdout='',
            stderr=str(e),
            traceback=str(e),
            exit_code=-1,
            execution_time=elapsed,
            success=False,
            timed_out=False
        )
