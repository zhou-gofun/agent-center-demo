from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from flask import Flask

fake_openai = types.ModuleType("openai")


class _DummyOpenAIClient:
    def __init__(self, *args, **kwargs):
        pass


fake_openai.OpenAI = _DummyOpenAIClient
fake_openai.AsyncOpenAI = _DummyOpenAIClient
sys.modules.setdefault("openai", fake_openai)

fake_chroma_store = types.ModuleType("vector_db.chroma_store")
fake_chroma_store.get_vector_store = lambda: None
sys.modules.setdefault("vector_db.chroma_store", fake_chroma_store)

fake_embeddings = types.ModuleType("vector_db.embeddings")
fake_embeddings.get_embedding_function = lambda: None
sys.modules.setdefault("vector_db.embeddings", fake_embeddings)

from src.api.routes import api_bp, registry_scanner


def _build_app():
    app = Flask(__name__)
    app.register_blueprint(api_bp)
    registry_scanner.scan()
    return app


def test_registry_scan_endpoint_returns_structured_report():
    app = _build_app()
    client = app.test_client()

    response = client.get("/v1/registry/scan")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert "healthy" in payload["data"]
    assert "errors" in payload["data"]


def test_chat_endpoint_validates_missing_query():
    app = _build_app()
    client = app.test_client()

    response = client.post("/v1/chat", json={})
    payload = response.get_json()

    assert response.status_code == 400
    assert payload["success"] is False
    assert payload["code"] == "missing_query"
