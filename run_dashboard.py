#!/usr/bin/env python3
"""Launch the IaCraft web dashboard."""

import os
import sys
import subprocess
import uvicorn
from dotenv import load_dotenv

load_dotenv()

PORT = int(os.getenv("DASHBOARD_PORT", "15000"))
HOST = os.getenv("DASHBOARD_HOST", "0.0.0.0")


def kill_port(port):
    """Kill any process holding the port."""
    try:
        if sys.platform == "win32":
            result = subprocess.run(
                f'netstat -ano | findstr ":{port} " | findstr "LISTEN"',
                capture_output=True, text=True, shell=True,
            )
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    pid = line.strip().split()[-1]
                    if pid and pid != "0":
                        subprocess.run(f"taskkill /f /pid {pid}", shell=True, capture_output=True)
        else:
            subprocess.run(f"fuser -k {port}/tcp", shell=True, capture_output=True)
    except Exception:
        pass


if __name__ == "__main__":
    kill_port(PORT)

    print(f"\n  IaCraft — Dashboard")
    print(f"  http://localhost:{PORT}\n")

    uvicorn.run(
        "src.dashboard.app:app",
        host=HOST,
        port=PORT,
    )
