"""Smoke check: prove the Meta Model API key works.

Harmless read-only call — lists the models this key can reach.
Run:  python3 -m server.smoke   (from the repo root, with .env loaded)
"""
from .config import MODEL_API_KEY, META_API_BASE_URL
from .meta_client import MetaClient


def main():
    client = MetaClient(MODEL_API_KEY, META_API_BASE_URL)
    data = client.list_models()
    models = data.get("data", data if isinstance(data, list) else [])
    names = [m.get("id", m) for m in models]
    print(f"OK — {len(names)} model(s) reachable with this key:")
    for name in names[:25]:
        print(f"  {name}")


if __name__ == "__main__":
    main()
