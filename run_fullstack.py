#!/usr/bin/env python3
"""Run the DESDEO backend (FastAPI) and frontend (SvelteKit) for local development.

Both processes run concurrently. Their output is prefixed with colored labels
so they can be distinguished. Press Ctrl+C to shut down both.

Run with --help to see the available options, e.g. --host 0.0.0.0 to expose
the servers on the network and --no-open to not launch a browser window.
"""

import argparse
import shutil
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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse the command line options."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind both servers to. Use 0.0.0.0 to expose them on the network (default: %(default)s).",
    )
    parser.add_argument("--port", type=int, default=8000, help="Backend port (default: %(default)s).")
    parser.add_argument(
        "--frontend-port",
        type=int,
        default=None,
        help="Frontend port (default: let Vite choose, usually 5173).",
    )
    parser.add_argument(
        "--no-open",
        dest="open_browser",
        action="store_false",
        help="Do not open a browser window for the frontend.",
    )
    parser.add_argument("--no-reload", dest="reload", action="store_false", help="Disable backend auto-reload.")
    parser.add_argument(
        "--log-level",
        default="debug",
        choices=["critical", "error", "warning", "info", "debug", "trace"],
        help="Backend log level (default: %(default)s).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the backend and frontend as subprocesses."""
    args = parse_args(argv)

    backend_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "app:app",
        "--log-level",
        args.log_level,
        "--host",
        args.host,
        "--port",
        str(args.port),
    ]
    if args.reload:
        backend_cmd.append("--reload")

    npm_path = shutil.which("npm")
    if npm_path is None:
        print(f"{RED}Could not find 'npm' on PATH. Is Node.js installed?{RESET}")  # noqa: T201
        return 1

    frontend_cmd = [npm_path, "run", "dev", "--", "--host", args.host]
    if args.frontend_port is not None:
        frontend_cmd += ["--port", str(args.frontend_port)]
    if args.open_browser:
        frontend_cmd.append("--open")

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
