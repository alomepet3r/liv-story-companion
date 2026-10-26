"""Modal deploy wrapper for the Day 1 Story Companion shell.

Status: PREPARED, NOT YET DEPLOYED. Deployment is one step once the
Modal account + API token exist — see deploy/README-modal.md.

How this wraps the existing app WITHOUT modifying it:
  * server/app.py is imported and run as-is. Its code on disk is
    untouched; the wrapper only adapts two runtime facts around it:
      1. PORT — the existing server already honours the PORT env var
         (default 8765); the wrapper sets PORT=8000 to match the port
         the @modal.web_server decorator exposes.
      2. Bind interface — the existing server binds 127.0.0.1, which is
         right for local use. Modal's web-server docs require the app
         inside the container to listen on the external interface
         (0.0.0.0), so the wrapper swaps the server class for one that
         binds 0.0.0.0 AT RUNTIME, in this file only. No application
         logic, handler, or route changes — same Handler, same code.

Image contents: ONLY the repo's server/ and web/ directories. The repo
.env file sits at the repo ROOT — outside both directories — so it is
structurally impossible for it to be copied into the image, and it is
also covered by .gitignore. The API key reaches the container
exclusively through the Modal Secret named "meta-model-api"
(key MODEL_API_KEY), injected as an environment variable, which
server/config.py already reads.

The app itself is Python standard library only. The `modal` SDK is
deploy-environment tooling (this file), not an app dependency.

Run (from the repo root, once the account/token/secret exist):
    modal deploy deploy/modal_app.py
"""

import os
import sys
from pathlib import Path

import modal

REPO_ROOT = Path(__file__).resolve().parent.parent
APP_HOME = "/root/app"          # where server/ and web/ land in the image
INTERNAL_PORT = 8000            # must match @modal.web_server below + PORT

image = (
    modal.Image.debian_slim(python_version="3.12")
    .add_local_dir(REPO_ROOT / "server", remote_path=f"{APP_HOME}/server")
    .add_local_dir(REPO_ROOT / "web", remote_path=f"{APP_HOME}/web")
)

app = modal.App("story-companion", image=image)


@app.function(
    secrets=[modal.Secret.from_name("meta-model-api")],
    # Keep ONE container warm around the clock so the demo never hits a
    # cold start. Needed for the event window Oct 26 – Nov 4, 2026
    # (pre-record Day 8, demo/submission days) — after the event this
    # can be relaxed to 0 to scale fully to zero when idle.
    min_containers=1,
)
@modal.web_server(INTERNAL_PORT, startup_timeout=60)
def serve():
    # Make `import server.app` resolve and let server/app.py find its
    # WEB_DIR exactly as it does locally (server/../web under APP_HOME).
    sys.path.insert(0, APP_HOME)
    os.chdir(APP_HOME)
    # The existing server honours PORT (see server/app.py main()).
    os.environ.setdefault("PORT", str(INTERNAL_PORT))

    import server.app as app_module

    # Runtime-only bind adaptation (see module docstring): same
    # ThreadingHTTPServer, same Handler — listening on 0.0.0.0 inside
    # the container instead of 127.0.0.1, as Modal's docs require.
    _real_server_class = app_module.ThreadingHTTPServer

    def _bind_all(address, handler, *args, **kwargs):
        return _real_server_class(("0.0.0.0", address[1]), handler,
                                  *args, **kwargs)

    app_module.ThreadingHTTPServer = _bind_all
    app_module.main()
