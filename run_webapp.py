"""
Entrypoint launcher for the YTL Power Satellite GEOINT & Alpha Web Application.
Launches the FastAPI backend on http://127.0.0.1:8000 using Uvicorn.
"""

import sys
import webbrowser
import uvicorn

# Ensure UTF-8 output encoding for Windows command line compatibility
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

def main():
    port = 8000
    host = "127.0.0.1"
    url = f"http://{host}:{port}"
    print("=" * 70)
    print(" [GEOINT] YTL Power (6742.KL) Satellite GEOINT & Alpha Tracker Webapp")
    print(f" [URL]    Starting server at: {url}")
    print("=" * 70)

    # Launch browser after slight delay in non-headless environments
    if "--no-browser" not in sys.argv:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    uvicorn.run("backend.app:app", host=host, port=port, reload=False, log_level="info")

if __name__ == "__main__":
    main()
