import sys
import os
import argparse
import webbrowser
import threading
import time
from pathlib import Path

# Force UTF-8 encoding for standard streams to avoid Windows CP1252 UnicodeEncodeError
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Handle pythonw / windowless execution where sys.stdout is None
if sys.stdout is None or sys.stderr is None:
    log_dir = PROJECT_ROOT / "data"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = open(log_dir / "server.log", "a", encoding="utf-8", buffering=1)
    if sys.stdout is None:
        sys.stdout = log_file
    if sys.stderr is None:
        sys.stderr = log_file

import uvicorn
from app.config import HOST, PORT

def open_browser(url: str, delay: float = 1.0):
    """Open browser in background after server has started."""
    time.sleep(delay)
    try:
        webbrowser.open(url)
    except Exception:
        pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Code Reviewer & Bug Detection Server")
    parser.add_argument("--host", type=str, default=HOST, help=f"Host to bind (default: {HOST})")
    parser.add_argument("--port", type=int, default=PORT, help=f"Port to bind (default: {PORT})")
    parser.add_argument("--reload", action="store_true", help="Enable live auto-reload on code change")
    parser.add_argument("--open-browser", action="store_true", help="Automatically open web browser on launch")
    args = parser.parse_args()

    display_host = "localhost" if args.host in ("0.0.0.0", "127.0.0.1") else args.host
    dashboard_url = f"http://{display_host}:{args.port}"

    print("=" * 70)
    print(">> Starting AI Code Review & Bug Detection System")
    print(f">> Dashboard URL:    {dashboard_url}")
    print(f">> Bound Interface: http://{args.host}:{args.port}")
    print(f">> Project Root:     {PROJECT_ROOT}")
    print(f">> Live Auto-Reload: {'ENABLED' if args.reload else 'DISABLED'}")
    print("=" * 70)

    if args.open_browser:
        threading.Thread(target=open_browser, args=(dashboard_url,), daemon=True).start()

    uvicorn.run("app.main:app", host=args.host, port=args.port, reload=args.reload)
