"""
TalentAI Desktop App — Production Entry Point
Serves pre-compiled Next.js static files via a local Python HTTP server,
runs the FastAPI backend locally, and opens a native pywebview desktop window.

This file is bundled into TalentAI.exe by PyInstaller.
"""
import os
import sys
import threading
import subprocess
import time
import http.server
import socketserver
import urllib.request
import logging

# ─── Determine Directory Roots FIRST (before any imports that depend on them) ──
if getattr(sys, 'frozen', False):
    # PyInstaller onedir: sys._MEIPASS is _internal dir
    BASE_DIR = sys._MEIPASS
    EXE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    EXE_DIR = BASE_DIR

# ─── Load the correct .env BEFORE anything else imports pydantic_settings ──────
# Priority: backend/.env inside the bundle (has real production credentials)
_candidate_envs = [
    os.path.join(BASE_DIR, "backend", ".env"),
    os.path.join(EXE_DIR, "backend", ".env"),
    os.path.join(BASE_DIR, ".env"),
    os.path.join(EXE_DIR, ".env"),
]
for _env_path in _candidate_envs:
    if os.path.isfile(_env_path):
        try:
            from dotenv import load_dotenv
            load_dotenv(_env_path, override=True)
        except ImportError:
            # Manual fallback: parse key=value lines into os.environ
            with open(_env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, _, val = line.partition("=")
                        os.environ.setdefault(key.strip(), val.strip())
        break  # Use first found

# ─── Logging Setup ─────────────────────────────────────────────────────────────
log_file = os.path.join(EXE_DIR, "TalentAI.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr),
        logging.FileHandler(log_file, encoding="utf-8", mode="a")
    ]
)
logger = logging.getLogger("TalentAI")

# ─── Auto-install pywebview if missing (dev mode only) ─────────────────────────
try:
    import webview
except ImportError:
    if not getattr(sys, 'frozen', False):
        logger.info("First-time setup: Installing UI dependencies...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pywebview"])
        import webview
    else:
        logger.critical("pywebview is not bundled in the exe. Cannot launch UI.")
        sys.exit(1)

PORT = 3000
BACKEND_PORT = 8000

# ─── Discover frontend/out ─────────────────────────────────────────────────────
FRONTEND_OUT = None
_frontend_candidates = [
    os.path.join(BASE_DIR, "frontend", "out"),       # _internal/frontend/out
    os.path.join(EXE_DIR, "frontend", "out"),         # dist/TalentAI/frontend/out
    os.path.join(EXE_DIR, "..", "..", "frontend", "out"),  # source tree fallback
]
for candidate in _frontend_candidates:
    real = os.path.realpath(candidate)
    if os.path.isdir(real) and os.path.isfile(os.path.join(real, "index.html")):
        FRONTEND_OUT = real
        logger.info(f"Frontend build found at: {FRONTEND_OUT}")
        break

# ─── Discover backend directory ────────────────────────────────────────────────
BACKEND_DIR = None
_backend_candidates = [
    os.path.join(BASE_DIR, "backend"),
    os.path.join(EXE_DIR, "backend"),
]
for candidate in _backend_candidates:
    if os.path.isdir(candidate) and os.path.isfile(os.path.join(candidate, "main.py")):
        BACKEND_DIR = candidate
        logger.info(f"Backend found at: {BACKEND_DIR}")
        break


class SilentNoCacheHandler(http.server.SimpleHTTPRequestHandler):
    """Static file handler with cache-busting headers and silent logging."""
    def end_headers(self):
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def log_message(self, format, *args):
        pass  # Suppress HTTP access logs in desktop mode

    def do_GET(self):
        """Serve index.html for unknown routes (SPA fallback)."""
        path = self.translate_path(self.path)
        # If the requested path doesn't exist on disk, serve index.html (Next.js routing)
        if not os.path.exists(path) or (os.path.isdir(path) and not os.path.isfile(os.path.join(path, "index.html"))):
            index_path = os.path.join(self.directory, "index.html")
            if os.path.exists(index_path):
                self.path = "/index.html"
        super().do_GET()


def is_url_alive(url, timeout=1.5):
    """Check if a URL responds with HTTP 200."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "TalentAI-HealthCheck"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def wait_for_service(url, name, max_wait=30.0):
    """Wait until an HTTP service responds 200 OK."""
    start_time = time.time()
    while time.time() - start_time < max_wait:
        if is_url_alive(url):
            logger.info(f"{name} is online and healthy.")
            return True
        time.sleep(0.5)
    logger.warning(f"Timeout waiting for {name} ({url}) after {max_wait}s.")
    return False


def start_static_server():
    """Start local HTTP server serving the Next.js static build."""
    if is_url_alive(f"http://127.0.0.1:{PORT}/"):
        logger.info(f"TalentAI static server already active on port {PORT}")
        return

    import functools
    handler = functools.partial(SilentNoCacheHandler, directory=FRONTEND_OUT)
    socketserver.TCPServer.allow_reuse_address = True
    try:
        with socketserver.TCPServer(("127.0.0.1", PORT), handler) as httpd:
            logger.info(f"TalentAI static server listening on http://127.0.0.1:{PORT}")
            httpd.serve_forever()
    except OSError as e:
        if e.errno == 10048:  # Windows: port already in use
            logger.warning(f"Port {PORT} already in use, assuming another instance is serving.")
        else:
            logger.error(f"Static server error: {e}")
    except Exception as e:
        logger.error(f"Static server error: {e}")


def start_backend_server():
    """Start the FastAPI backend server using Uvicorn."""
    if is_url_alive(f"http://127.0.0.1:{BACKEND_PORT}/api/v1/health"):
        logger.info(f"TalentAI backend server already active on port {BACKEND_PORT}")
        return

    if BACKEND_DIR and BACKEND_DIR not in sys.path:
        sys.path.insert(0, BACKEND_DIR)

    original_dir = os.getcwd()
    try:
        if BACKEND_DIR:
            os.chdir(BACKEND_DIR)

        # Ensure dotenv is loaded for the backend working directory
        try:
            from dotenv import load_dotenv
            backend_env = os.path.join(BACKEND_DIR, ".env") if BACKEND_DIR else None
            if backend_env and os.path.isfile(backend_env):
                load_dotenv(backend_env, override=True)
        except ImportError:
            pass

        import uvicorn
        from main import app
        logger.info(f"Starting TalentAI backend server on http://127.0.0.1:{BACKEND_PORT}")
        uvicorn.run(app, host="127.0.0.1", port=BACKEND_PORT, log_level="warning")
    except Exception as e:
        import traceback
        logger.error(f"Failed to start backend server: {e}\n{traceback.format_exc()}")
    finally:
        os.chdir(original_dir)


def show_error_dialog(title, message):
    """Show an error dialog to the user, works even without console."""
    logger.critical(f"{title}: {message}")
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        messagebox.showerror(title, message)
        root.destroy()
    except Exception:
        pass


def main():
    try:
        logger.info("=" * 60)
        logger.info("TalentAI Desktop App starting...")
        logger.info(f"  BASE_DIR (MEIPASS): {BASE_DIR}")
        logger.info(f"  EXE_DIR:            {EXE_DIR}")
        logger.info(f"  FRONTEND_OUT:       {FRONTEND_OUT}")
        logger.info(f"  BACKEND_DIR:        {BACKEND_DIR}")
        logger.info(f"  Python:             {sys.executable}")
        logger.info(f"  Frozen:             {getattr(sys, 'frozen', False)}")
        logger.info("=" * 60)

        # Validate frontend build exists
        if not FRONTEND_OUT:
            show_error_dialog(
                "TalentAI — Missing Frontend",
                f"Frontend build (frontend/out) not found.\n\n"
                f"Searched in:\n" + "\n".join(f"  • {c}" for c in _frontend_candidates) +
                f"\n\nPlease rebuild: cd frontend && npm run build"
            )
            sys.exit(1)

        # Validate backend exists
        if not BACKEND_DIR:
            show_error_dialog(
                "TalentAI — Missing Backend",
                "Backend directory with main.py not found.\n\n"
                "Please rebuild the application."
            )
            sys.exit(1)

        # 1. Start the static file server
        server_thread = threading.Thread(target=start_static_server, daemon=True)
        server_thread.start()

        # 2. Start the backend server
        backend_thread = threading.Thread(target=start_backend_server, daemon=True)
        backend_thread.start()

        # 3. Wait until both services are alive
        frontend_ok = wait_for_service(f"http://127.0.0.1:{PORT}/", "Frontend Static Server", max_wait=15)
        backend_ok = wait_for_service(f"http://127.0.0.1:{BACKEND_PORT}/api/v1/health", "FastAPI Backend", max_wait=30)

        if not frontend_ok:
            show_error_dialog(
                "TalentAI — Frontend Failed",
                f"The frontend server did not start on port {PORT}.\n"
                "Check TalentAI.log for details."
            )
            sys.exit(1)

        if not backend_ok:
            logger.warning("Backend not yet healthy — launching UI anyway (may load with errors).")

        # 4. Create the native desktop window with resilient browser fallback
        try:
            window = webview.create_window(
                title='TalentAI — Enterprise Recruitment',
                url=f'http://127.0.0.1:{PORT}/?t={int(time.time())}',
                width=1440,
                height=860,
                min_size=(1100, 700),
                frameless=False,
                text_select=True,
                background_color='#0A0A0A',
                zoomable=True,
            )
            webview.start(debug=False)
            logger.info("TalentAI desktop window closed. Exiting.")
        except Exception as win_err:
            logger.warning(f"Native desktop window unavailable ({win_err}). Opening in default web browser...")
            import webbrowser
            webbrowser.open(f'http://127.0.0.1:{PORT}/')
            # Keep backend/frontend services running
            while True:
                time.sleep(2)

    except Exception as e:
        import traceback
        err_msg = traceback.format_exc()
        logger.critical(f"Unhandled crash:\n{err_msg}")
        show_error_dialog(
            "TalentAI Startup Error",
            f"A fatal error occurred:\n\n{e}\n\nSee TalentAI.log for full details."
        )

    finally:
        # Clean exit — flush logs, then terminate
        logging.shutdown()
        os._exit(0)


if __name__ == '__main__':
    main()
