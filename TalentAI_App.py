import os
import sys
import threading
import subprocess
import time
import http.server
import socketserver

# Auto-install pywebview if not present
try:
    import webview
except ImportError:
    print("First-time setup: Installing UI dependencies...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pywebview"])
    import webview

PORT = 3000

class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

def start_static_server():
    """Serves the compiled Next.js static files directly."""
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'frontend', 'out')
    os.chdir(out_dir)
    with socketserver.TCPServer(("", PORT), NoCacheHandler) as httpd:
        httpd.serve_forever()

def main():
    print("Initializing TalentAI Ecosystem...")
    
    # Boot up the lightning-fast static Python server
    server_thread = threading.Thread(target=start_static_server, daemon=True)
    server_thread.start()
    
    time.sleep(1)  # Takes <1 second to boot
    
    # Create the native desktop window
    window = webview.create_window(
        title='TalentAI - Enterprise Recruitment',
        url=f'http://localhost:{PORT}',
        width=1280,
        height=800,
        min_size=(900, 600),
        frameless=False,
        text_select=True,
        background_color='#0A0A0A'
    )
    
    # Start the application
    webview.start()

if __name__ == '__main__':
    main()
