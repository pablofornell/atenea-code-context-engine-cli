import shutil
import platform
import getpass
import sys
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any

def run_command(command, shell=True):
    print(f"Running: {command}")
    try:
        if isinstance(command, list):
            subprocess.check_call(command)
        else:
            subprocess.check_call(command, shell=shell)
    except subprocess.CalledProcessError as e:
        print(f"Error: Command failed with exit code {e.returncode}")
        return False
    return True

def setup():
    is_windows = platform.system() == "Windows"
    python_cmd = sys.executable
    venv_dir = Path(".venv")
    venv_python = venv_dir / ("Scripts/python.exe" if is_windows else "bin/python")
    
    print(f"--- Setting up Atenea CLI ({platform.system()}) ---")

    # 1. Aggressive Cleanup
    print("--- Cleaning up old build artifacts and venv ---")
    for d in ["build", "atenea_cli.egg-info", "atenea.egg-info", "dist", ".venv"]:
        dir_path = Path(d)
        if dir_path.exists():
            try:
                shutil.rmtree(dir_path)
                print(f"  Deleted {d}")
            except Exception as e:
                print(f"  Warning: Could not delete {d}: {e}")

    # 2. Create Venv
    print("--- Creating Virtual Environment ---")
    if not run_command([python_cmd, "-m", "venv", str(venv_dir)]):
        return

    # Verify venv creation
    if not (venv_dir / "pyvenv.cfg").exists():
        print("Error: venv creation failed - pyvenv.cfg not found.")
        return

    # 3. Upgrade pip and install dependencies
    print("--- Upgrading pip and setuptools ---")
    run_command([str(venv_python), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "build"])

    # 4. Install dependencies in editable mode
    print("--- Installing package in editable mode ---")
    if not run_command([str(venv_python), "-m", "pip", "install", "-e", "."]):
        return

    print("\n--- Setup Complete! ---")
    bin_name = "atenea.exe" if is_windows else "atenea"
    atenea_path = venv_dir / ("Scripts" if is_windows else "bin") / bin_name
    print(f"To run the CLI, use: {atenea_path}")

if __name__ == "__main__":
    setup()
