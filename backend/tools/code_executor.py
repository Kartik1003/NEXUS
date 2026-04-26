"""Safe code execution via subprocess."""
import subprocess
import tempfile
import time
import os
from core.models import CodeExecutionResult
from config import CODE_EXECUTION_TIMEOUT


async def execute_python(code: str, timeout: int = CODE_EXECUTION_TIMEOUT) -> CodeExecutionResult:
    """Execute Python code in a subprocess with timeout."""
    start = time.time()

    # Write code to temp file
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(code)
        tmp_path = f.name

    try:
        result = subprocess.run(
            ["python", tmp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=tempfile.gettempdir(),
        )
        elapsed = time.time() - start

        return CodeExecutionResult(
            success=result.returncode == 0,
            stdout=result.stdout[:5000],  # Cap output size
            stderr=result.stderr[:3000],
            return_code=result.returncode,
            execution_time=round(elapsed, 3),
        )
    except subprocess.TimeoutExpired:
        return CodeExecutionResult(
            success=False,
            stderr=f"Execution timed out after {timeout}s",
            return_code=-1,
            execution_time=timeout,
        )
    except Exception as e:
        return CodeExecutionResult(
            success=False,
            stderr=str(e),
            return_code=-1,
            execution_time=time.time() - start,
        )
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
