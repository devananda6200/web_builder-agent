import pathlib
import subprocess
from typing import Tuple

from langchain_core.tools import tool

PROJECT_ROOT = pathlib.Path.cwd() / "generated_project"


def safe_path_for_project(path: str) -> pathlib.Path:
    p = (PROJECT_ROOT / path).resolve()
    if PROJECT_ROOT.resolve() not in p.parents and PROJECT_ROOT.resolve() != p.parent and PROJECT_ROOT.resolve() != p:
        raise ValueError("Attempt to write outside project root")
    return p


@tool
def write_file(path: str, content: str) -> str:
    """Writes content to a file at the specified path within the project root."""
    p = safe_path_for_project(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(content)
    return f"WROTE:{p}"


@tool
def edit_file(path: str, old_snippet: str, new_snippet: str) -> str:
    """Edits a file by replacing an exact string match of old_snippet with new_snippet. Make sure old_snippet matches exactly, including indention."""
    p = safe_path_for_project(path)
    if not p.exists():
        return f"ERROR: File {p} does not exist. Use write_file to create it."
    with open(p, "r", encoding="utf-8") as f:
        content = f.read()
    
    if old_snippet not in content:
        return f"ERROR: old_snippet not found in {p}. Ensure exact match including whitespace."
    
    if content.count(old_snippet) > 1:
        return f"ERROR: old_snippet found multiple times in {p}. Please make the snippet more unique."
        
    new_content = content.replace(old_snippet, new_snippet, 1)
    with open(p, "w", encoding="utf-8") as f:
        f.write(new_content)
    return f"SUCCESSFULLY EDITED:{p}"


@tool
def read_file(path: str) -> str:
    """Reads content from a file at the specified path within the project root."""
    p = safe_path_for_project(path)
    if not p.exists():
        return ""
    with open(p, "r", encoding="utf-8") as f:
        return f.read()


@tool
def get_current_directory() -> str:
    """Returns the current working directory."""
    return str(PROJECT_ROOT)


@tool
def list_files(directory: str = ".") -> str:
    """Lists all files in the specified directory within the project root."""
    p = safe_path_for_project(directory)
    if not p.is_dir():
        return f"ERROR: {p} is not a directory"
    files = [str(f.relative_to(PROJECT_ROOT)) for f in p.glob("**/*") if f.is_file()]
    return "\n".join(files) if files else "No files found."

@tool
def list_file(directory: str = ".") -> str:
    """Alias for list_files. Lists all files in the specified directory."""
    p = safe_path_for_project(directory)
    if not p.is_dir():
        return f"ERROR: {p} is not a directory"
    files = [str(f.relative_to(PROJECT_ROOT)) for f in p.glob("**/*") if f.is_file()]
    return "\n".join(files) if files else "No files found."

from typing import Tuple, Union

@tool
def search_files(query: str, path: str = ".", max_results: int = 20) -> str:
    """Searches for files matching a query in the specified directory."""
    try:
        p = safe_path_for_project(path) if path else PROJECT_ROOT
    except:
        p = PROJECT_ROOT
        
    if not p.is_dir():
        return f"ERROR: {path} is not a valid directory."
        
    files = []
    query_lower = query.lower()
    for f in p.glob("**/*"):
        if f.is_file() and query_lower in f.name.lower():
            files.append(str(f.relative_to(PROJECT_ROOT)))
            if len(files) >= max_results:
                break
                
    return "\n".join(files) if files else "No matching files found."

@tool
def run_cmd(cmd: Union[str, list], cwd: str | None = None, timeout: int = 30) -> Tuple[int, str, str]:
    """Runs a shell command in the specified directory and returns the result."""
    if isinstance(cmd, list):
        cmd = " ".join(str(c) for c in cmd)
        
    cwd_dir = safe_path_for_project(cwd) if cwd else PROJECT_ROOT
    res = subprocess.run(cmd, shell=True, cwd=str(cwd_dir), capture_output=True, text=True, timeout=timeout)
    return res.returncode, res.stdout, res.stderr


def init_project_root():
    PROJECT_ROOT.mkdir(parents=True, exist_ok=True)
    return str(PROJECT_ROOT)
