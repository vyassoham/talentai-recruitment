"""
TalentAI Desktop App — Production Entry Point
Serves pre-compiled Next.js static files via a local Python HTTP server,
then opens a native pywebview desktop window.

This file is bundled into TalentAI.exe by PyInstaller.
"""
import os
import sys
import threading
import subprocess
import time
import http.server
import socketserver
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Auto-install pywebview if missing (only in dev mode, not in exe)
try:
    import webview
except ImportError:
    print("First-time setup: Installing UI dependencies...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pywebview"])
    import webview

PORT = 3000

# ─── Determine the frontend/out directory ────────────────────────────────────
# When running as PyInstaller .exe, sys._MEIPASS holds the temp extract dir.
# When running as plain .py, use relative path.
if getattr(sys, 'frozen', False):
    # Running inside .exe
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FRONTEND_OUT = os.path.join(BASE_DIR, "frontend", "out")

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
        if not os.path.exists(path) or os.path.isdir(path):
            index_path = os.path.join(FRONTEND_OUT, "index.html")
            if os.path.exists(index_path):
                self.path = "/index.html"
        super().do_GET()


def start_static_server():
    """Start local HTTP server serving the Next.js static build."""
    original_dir = os.getcwd()
    os.chdir(FRONTEND_OUT)
    try:
        # Allow address reuse to avoid "already in use" on restart
        socketserver.TCPServer.allow_reuse_address = True
        with socketserver.TCPServer(("127.0.0.1", PORT), SilentNoCacheHandler) as httpd:
            logger.info(f"TalentAI static server → http://127.0.0.1:{PORT}")
            httpd.serve_forever()
    finally:
        os.chdir(original_dir)


def main():
    # Validate frontend build exists
    if not os.path.exists(FRONTEND_OUT):
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "TalentAI — Missing Frontend",
            f"Frontend build not found at:\n{FRONTEND_OUT}\n\n"
            "Please run 'npm run build' in the frontend directory first."
        )
        sys.exit(1)

    logger.info("Starting TalentAI Desktop App...")

    # Start the static file server in background thread
    server_thread = threading.Thread(target=start_static_server, daemon=True)
    server_thread.start()
    time.sleep(0.8)  # Brief wait for server to bind

    # Create the native desktop window — no browser chrome, full-width
    window = webview.create_window(
        title='TalentAI — Enterprise Recruitment',
        url=f'http://127.0.0.1:{PORT}/?t={int(time.time())}',
        width=1440,          # Wider default so nav fits without clipping
        height=860,
        min_size=(1100, 700),
        frameless=False,
        text_select=True,
        background_color='#0A0A0A',
        zoomable=True,       # Allow Ctrl+scroll zoom
    )

    # Start pywebview event loop (blocks until window closed)
    webview.start(debug=False)
    logger.info("TalentAI window closed. Exiting.")


if __name__ == '__main__':
    main()
