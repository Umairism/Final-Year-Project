from types import SimpleNamespace

from fastapi.testclient import TestClient

from api.app import app
from api.routes import ai
from api.services import gemini_service


def test_gemini_chat_uses_shared_service(monkeypatch):
    calls = []

    async def generate(system, prompt, **kwargs):
        calls.append((system, prompt, kwargs))
        return 'OK'

    monkeypatch.setattr(gemini_service, 'generate_text', generate)
    monkeypatch.setattr(ai, 'get_settings', lambda: SimpleNamespace(GEMINI_MODEL='test-flash-lite'))
    response = TestClient(app).post('/api/v1/ai/chat', json={
        'provider': 'gemini', 'system_prompt': 'system', 'prompt': 'prompt', 'max_tokens': 64,
    })
    assert response.status_code == 200
    assert response.json() == {'provider': 'gemini', 'model': 'test-flash-lite', 'content': 'OK'}
    assert calls == [('system', 'prompt', {'max_output_tokens': 64})]


def test_gemini_chat_upstream_error_sanitized(monkeypatch):
    async def generate(*args, **kwargs):
        raise gemini_service.GeminiUpstreamError('PRIVATE_KEY PRIVATE_BODY', status_code=503)

    monkeypatch.setattr(gemini_service, 'generate_text', generate)
    response = TestClient(app).post('/api/v1/ai/chat', json={'provider': 'gemini', 'prompt': 'test'})
    assert response.status_code == 502
    assert response.json() == {'detail': 'Gemini upstream request failed.'}
    assert 'PRIVATE' not in response.text


def test_gemini_chat_not_configured(monkeypatch):
    async def generate(*args, **kwargs):
        raise gemini_service.GeminiNotConfiguredError()

    monkeypatch.setattr(gemini_service, 'generate_text', generate)
    response = TestClient(app).post('/api/v1/ai/chat', json={'provider': 'gemini', 'prompt': 'test'})
    assert response.status_code == 400
    assert response.json() == {'detail': 'GEMINI_API_KEY is not configured'}
