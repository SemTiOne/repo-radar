"""
deploy/server_entrypoint.py — Entrypoint for the RepoRadar license + webhook server.
"""

import os
import sys

sys.path.insert(0, "/app")

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import both sub-apps
from licensing.key_server import app as license_app
from licensing.webhook_server import app as webhook_app

# Build combined app by registering all routes
main_app = FastAPI(title="RepoRadar Server", docs_url=None, redoc_url=None)

main_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Copy routes from both sub-apps into main_app
for route in license_app.routes:
    main_app.router.routes.append(route)

for route in webhook_app.routes:
    main_app.router.routes.append(route)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))

    required_env_vars = [
        "LICENSE_SERVER_SECRET",
        "API_AUTH_TOKEN",
        "RESEND_API_KEY",
        "KOFI_VERIFICATION_TOKEN",
    ]
    missing = [v for v in required_env_vars if not os.environ.get(v)]
    if missing:
        print(f"ERROR: Missing env vars: {', '.join(missing)}")
        sys.exit(1)

    print(f"Starting RepoRadar Server on :{port}")
    print("  Routes: /health, /validate, /revoke, /kofi/webhook, /webhook/health")
    uvicorn.run("server_entrypoint:main_app", host="0.0.0.0", port=port, log_level="info")
