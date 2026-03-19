import os
import subprocess
import sys
import platform

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
    python_cmd = "python" if is_windows else "python3"
    venv_dir = ".venv"
    pip_cmd = os.path.join(venv_dir, "Scripts", "pip") if is_windows else os.path.join(venv_dir, "bin", "pip")
    
    print(f"--- Setting up Atenea CLI ({platform.system()}) ---")

    # 1. Create Venv
    if not os.path.exists(venv_dir):
        if not run_command(f"{python_cmd} -m venv {venv_dir}"):
            return

    # 2. Install dependencies in editable mode
    if not run_command(f"{pip_cmd} install -e ."):
        return

    print("\n--- Setup Complete! ---")
    print(f"To run the CLI, use: {os.path.join(venv_dir, 'Scripts', 'atenea') if is_windows else os.path.join(venv_dir, 'bin', 'atenea')}")

if __name__ == "__main__":
    setup()
