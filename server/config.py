"""Fireside hackathon build — configuration.

Secrets come from the environment only. Never hardcode keys.
"""
import os

META_API_BASE_URL = os.environ.get("META_API_BASE_URL",
                                   "https://api.meta.ai/v1")
MODEL_API_KEY = os.environ.get("MODEL_API_KEY", "")

# Chat model ID. The exact catalog depends on your key's entitlements —
# `python3 -m server.smoke` lists what your key can reach.
CHAT_MODEL = os.environ.get("FIRESIDE_CHAT_MODEL", "muse-spark-1.3")
