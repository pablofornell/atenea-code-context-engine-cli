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
    venv_python = os.path.join(venv_dir, "Scripts", "python") if is_windows else os.path.join(venv_dir, "bin", "python")
    
    print(f"--- Setting up Atenea CLI ({platform.system()}) ---")

    # 1. Clean up stale build artifacts that can cause issues on Windows
    print("--- Cleaning up old build artifacts ---")
    import shutil
    for d in ["build", "atenea_cli.egg-info", "atenea.egg-info", "dist"]:
        if os.path.exists(d):
            try:
                shutil.rmtree(d)
                print(f"  Deleted {d}")
            except Exception:
                pass

    # 2. Create Venv (Force clear if exists to avoid broken states)
    print("--- Creating Virtual Environment ---")
    if not run_command(f"{python_cmd} -m venv --clear {venv_dir}"):
        return

    # 3. Upgrade pip and setuptools and install 'build'
    print("--- Upgrading pip and setuptools ---")
    run_command(f"{venv_python} -m pip install --upgrade pip setuptools build")

    # 4. Install dependencies in editable mode
    if not run_command(f"{venv_python} -m pip install -e ."):
        return

    print("\n--- Setup Complete! ---")
    print(f"To run the CLI, use: {os.path.join(venv_dir, 'Scripts', 'atenea') if is_windows else os.path.join(venv_dir, 'bin', 'atenea')}")

if __name__ == "__main__":
    setup()
