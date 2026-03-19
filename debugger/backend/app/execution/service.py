from dataclasses import dataclass
import docker
import docker.errors
import requests.exceptions
import tarfile
import io
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

        # Build tar archive containing the submission
        tar_stream = io.BytesIO()
        with tarfile.open(fileobj=tar_stream, mode='w') as tar:
            code_bytes = code.encode('utf-8')
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
            # Allow writes only to /tmp where the submission lives
            tmpfs={'/tmp': 'size=16m,noexec'},
            security_opt=['no-new-privileges:true'],
            detach=True,
        )

        try:
            container.put_archive('/tmp', tar_stream)
            container.start()

            timed_out = False
            try:
                result = container.wait(timeout=settings.SANDBOX_TIMEOUT_SECONDS)
                exit_code = result.get('StatusCode', 0)
            except requests.exceptions.ReadTimeout:
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

            # Fetch stdout and stderr as separate streams
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
            # Always remove the container regardless of what happened above
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
    except Exception as e:
        elapsed = time.time() - start
        return ExecutionResult(
            stdout='', stderr=str(e), traceback=str(e),
            exit_code=-1, execution_time=elapsed,
            success=False, timed_out=False,
        )
