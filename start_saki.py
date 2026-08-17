#!/usr/bin/env python3
"""
Saki AI All-in-One Master Launcher
Running this file automatically sets up missing dependencies,
launches the FastAPI backend and Next.js frontend, and opens the browser.
"""

import os
import sys
import time
import subprocess
import webbrowser

ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
VENV_DIR = os.path.join(ROOT_DIR, "venv")
VENV_PYTHON = os.path.join(VENV_DIR, "Scripts", "python.exe") if os.name == "nt" else os.path.join(VENV_DIR, "bin", "python")
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")
NODE_MODULES = os.path.join(FRONTEND_DIR, "node_modules")


def check_and_setup_venv():
    if not os.path.exists(VENV_DIR) or not os.path.exists(VENV_PYTHON):
        print("[*] Virtual environment 'venv' not found. Creating venv...")
        subprocess.run([sys.executable, "-m", "venv", VENV_DIR], check=True)
        print("[*] Installing Python requirements...")
        subprocess.run([VENV_PYTHON, "-m", "pip", "install", "--upgrade", "pip"], check=True)
        subprocess.run([VENV_PYTHON, "-m", "pip", "install", "-r", os.path.join(ROOT_DIR, "requirements.txt")], check=True)
    else:
        print("[OK] Python virtual environment verified.")


def check_and_setup_frontend():
    if not os.path.exists(NODE_MODULES):
        print("[*] Frontend node_modules not found. Running npm install...")
        cmd = "cmd /c npm install" if os.name == "nt" else "npm install"
        subprocess.run(cmd, cwd=FRONTEND_DIR, shell=True, check=True)
    else:
        print("[OK] Frontend dependencies verified.")


def launch_all():
    print("\n[*] Launching Saki AI Companion...")
    
    # 1. Start Backend
    print("  [1/2] Starting FastAPI Backend on http://localhost:8000 ...")
    backend_cmd = f'"{VENV_PYTHON}" -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload'
    if os.name == "nt":
        subprocess.Popen(f'start "Saki Backend" cmd /k "{backend_cmd}"', shell=True, cwd=ROOT_DIR)
    else:
        subprocess.Popen(backend_cmd, shell=True, cwd=ROOT_DIR)

    time.sleep(2)

    # 2. Start Frontend
    print("  [2/2] Starting Next.js Frontend on http://localhost:3000 ...")
    frontend_cmd = "cmd /c npm run dev" if os.name == "nt" else "npm run dev"
    if os.name == "nt":
        subprocess.Popen(f'start "Saki Frontend" cmd /k "{frontend_cmd}"', shell=True, cwd=FRONTEND_DIR)
    else:
        subprocess.Popen(frontend_cmd, shell=True, cwd=FRONTEND_DIR)

    time.sleep(3)

    # 3. Open Browser
    print("[*] Opening Saki AI in your browser at http://localhost:3000 ...")
    webbrowser.open("http://localhost:3000")

    print("\n===================================================")
    print("  Saki AI Companion is running!")
    print("  - Backend:  http://localhost:8000")
    print("  - Frontend: http://localhost:3000")
    print("===================================================\n")


if __name__ == "__main__":
    check_and_setup_venv()
    check_and_setup_frontend()
    launch_all()
