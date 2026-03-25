import subprocess
from pathlib import Path
from typing import Optional

def get_project_type(target_dir: Path = Path.cwd()) -> str:
    """Determine the project type based on configuration files."""
    if (target_dir / "package.json").exists():
        return "web"
    if (target_dir / "requirements.txt").exists() or (target_dir / "pyproject.toml").exists() or (target_dir / "main.py").exists():
        return "ai"
    return "unknown"

def run_cmd(command: list[str] | str, cwd: Optional[Path] = None, shell: bool = False, capture: bool = True) -> subprocess.CompletedProcess:
    """Unified helper for running subprocess commands."""
    return subprocess.run(
        command, 
        cwd=cwd, 
        shell=shell, 
        check=True, 
        capture_output=capture, 
        text=True
    )