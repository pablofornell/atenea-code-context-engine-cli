import os
from typing import Optional

def get_project_root(start_path: Optional[str] = None) -> str:
    """
    Search upwards from start_path (or CWD) to find the project root.
    A project root is defined by the presence of .git, pyproject.toml, or Makefile.
    """
    if start_path is None:
        start_path = os.getcwd()
    
    current = os.path.abspath(start_path)
    
    # Common markers for project root
    markers = {".git", "pyproject.toml", "Makefile", "setup.py", "install.py", "package.json"}
    
    while True:
        if any(os.path.exists(os.path.join(current, m)) for m in markers):
            return current
        
        parent = os.path.dirname(current)
        if parent == current: # Reached filesystem root
            return os.path.abspath(start_path)
        current = parent
    
    return os.path.abspath(start_path)
