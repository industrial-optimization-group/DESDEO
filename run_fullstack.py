#!/usr/bin/env python3
"""Run the DESDEO backend (FastAPI) and frontend (SvelteKit) for local development.

Both processes run concurrently. Their output is prefixed with colored labels
so they can be distinguished. Press Ctrl+C to shut down both.
"""

import signal
import subprocess
import sys
import threading
from pathlib import Path

# ANSI color codes (work on Windows 10+ with VT support, macOS, Linux)
BLUE = "\033[0;34m"
YELLOW = "\033[0;33m"
RED = "\033[0;31m"
RESET = "\033[0m"

ROOT = Path(__file__).resolve().parent


def stream_output(process: subprocess.Popen, label: str, color: str) -> None:
    """Read lines from a process's stdout and print them with a colored prefix."""
    assert process.stdout is not None  # noqa: S101
    for line in process.stdout:
        print(f"{color}({label}){RESET} {line}", end="", flush=True)  # noqa: T201


def main() -> int:
    """Run the backend and frontend as subprocesses."""
    backend_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "app:app",
        "--reload",
        "--log-level",
        "debug",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
    ]
    frontend_cmd = ["npm", "run", "dev", "--", "--open"]

    procs: list[subprocess.Popen] = []

    try:
        backend = subprocess.Popen(  # noqa: S603
            backend_cmd,
            cwd=ROOT / "desdeo" / "api",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        procs.append(backend)

        frontend = subprocess.Popen(  # noqa: S603
            frontend_cmd,
            cwd=ROOT / "webui",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        procs.append(frontend)

        # Stream output in background threads so both are printed concurrently.
        threads = [
            threading.Thread(target=stream_output, args=(backend, "Backend", BLUE), daemon=True),
            threading.Thread(target=stream_output, args=(frontend, "Frontend", YELLOW), daemon=True),
        ]
        for t in threads:
            t.start()

        # Wait for either process to exit.
        while all(p.poll() is None for p in procs):
            for t in threads:
                t.join(timeout=0.5)

    except KeyboardInterrupt:
        print(f"\n{RED}Shutting down...{RESET}")  # noqa: T201
    finally:
        for p in procs:
            p.terminate()
        for p in procs:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()

    return 0


if __name__ == "__main__":
    # Allow Ctrl+C to propagate cleanly on Windows.
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    raise SystemExit(main())
