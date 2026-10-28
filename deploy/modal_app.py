"""Modal deploy wrapper for the Day 1 Story Companion shell.

Status: DEPLOYED (live since Oct 26, 2026; fleet pinned to a single
container Oct 28, 2026 — see the @app.function comment). Runbook:
deploy/README-modal.md.

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


# Launcher run as a SUBPROCESS inside the container. Modal's web_server
# contract requires a NON-BLOCKING start (subprocess.Popen): the earlier
# version called the app's blocking serve_forever() in-process, Modal
# logged "Runner has been initializing for too long… use a
# non-blocking call such as subprocess.Popen" and crash-looped the
# containers (diagnosed Oct 26, 2026, from `modal app logs`). The
# launcher imports server/app.py as-is and applies the runtime-only
# 0.0.0.0 bind swap in the subprocess — application code untouched.
LAUNCHER = r"""
import sys
sys.path.insert(0, "/root/app")
import server.app as m

class _BindAll(m.ThreadingHTTPServer):
    def __init__(self, address, handler, *args, **kwargs):
        super().__init__(("0.0.0.0", address[1]), handler, *args, **kwargs)

m.ThreadingHTTPServer = _BindAll
m.main()
"""


@app.function(
    secrets=[modal.Secret.from_name("meta-model-api")],
    # Keep ONE container warm around the clock so the demo never hits a
    # cold start. Needed for the event window Oct 26 – Nov 4, 2026
    # (pre-record Day 8, demo/submission days) — after the event this
    # can be relaxed to 0 to scale fully to zero when idle.
    min_containers=1,
    # PIN THE FLEET TO ONE CONTAINER (Oct 28, 2026 — Skunkworks Rounds
    # 1+2, Top Move #1). Sessions, media, chapters and keepsake tokens
    # all live in one container's memory (server/app.py). With only
    # min_containers=1, load bursts spawned extra containers and a
    # storyteller's session silently landed on an amnesiac container —
    # reproduced live twice (Round 1 K4/K6, Round 2 Cell 5: after a
    # 12-way burst the seeded session denied the name and story it had
    # acknowledged minutes earlier). max_containers=1 makes every
    # request land on the single warm container, so in-memory state is
    # coherent for the whole hackathon window. The long scaledown
    # window keeps that container from cycling mid-window. Trade-off
    # accepted for the window: throughput is capped at one container's
    # ThreadingHTTPServer, which the demo + judging traffic fits.
    # REMOVE after the event window (scale-out becomes safe only once
    # state moves out of container memory).
    max_containers=1,
    scaledown_window=3600,
)
@modal.web_server(INTERNAL_PORT, startup_timeout=120)
def serve():
    import subprocess

    env = dict(os.environ, PORT=str(INTERNAL_PORT))
    subprocess.Popen([sys.executable, "-c", LAUNCHER],
                     cwd=APP_HOME, env=env)
