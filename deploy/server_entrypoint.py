"""
deploy/server_entrypoint.py — Entrypoint for the RepoRadar license server.

Starts the FastAPI license validation server on the PORT provided by Railway.
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    
    # Validate required env vars on startup
    missing = []
    if not os.environ.get("LICENSE_SERVER_SECRET"):
        missing.append("LICENSE_SERVER_SECRET")
    if not os.environ.get("API_AUTH_TOKEN"):
        missing.append("API_AUTH_TOKEN")
    
    if missing:
        print(f"ERROR: Missing required environment variables: {', '.join(missing)}")
        print("Set these in your Railway dashboard under Variables.")
        sys.exit(1)
    
    print(f"Starting RepoRadar License Server on port {port}...")
    uvicorn.run(
        "licensing.key_server:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
    )