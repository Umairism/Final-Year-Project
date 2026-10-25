import asyncio
import json
import logging
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient

from api.app import app
from api.models.database import get_db
from api.routes import ai
from api.services import gemini_service


@pytest.fixture
def mock_google(monkeypatch):
    monkeypatch.setattr(gemini_service, 'get_settings', lambda: SimpleNamespace(
        GEMINI_API_KEY='TEST_KEY_SENTINEL', GEMINI_MODEL='test-model'))
    original_client = httpx.AsyncClient

    def install(handler):
        monkeypatch.setattr(gemini_service.httpx, 'AsyncClient',
                            lambda **kwargs: original_client(
                                transport=httpx.MockTransport(handler), **kwargs))
    return install


def test_success_preserves_body_and_header(mock_google):
    def handler(request):
        assert request.headers['x-goog-api-key'] == 'TEST_KEY_SENTINEL'
        assert 'TEST_KEY_SENTINEL' not in str(request.url)
        assert request.url.path == '/v1beta/models/test-model:generateContent'
        assert json.loads(request.content) == {
            'system_instruction': {'parts': [{'text': 'system'}]},
            'contents': [{'role': 'user', 'parts': [{'text': 'prompt'}]}],
            'generationConfig': {'maxOutputTokens': 16, 'temperature': 0.2},
        }
        return httpx.Response(200, json={'candidates': [
            {'content': {'parts': [{'text': 'OK'}]}}]})

    mock_google(handler)
    assert asyncio.run(gemini_service.generate_text('system', 'prompt', max_output_tokens=16)) == 'OK'


def forbidden(request):
    return httpx.Response(403, json={'error': {
        'status': 'PERMISSION_DENIED',
        'message': 'TEST_KEY_SENTINEL PRIVATE_BODY PRIVATE_PROMPT',
        'details': [{'reason': 'API_KEY_SERVICE_BLOCKED'}],
    }})


def test_403_attributes_and_single_safe_warning(mock_google, caplog):
    mock_google(forbidden)
    with caplog.at_level(logging.WARNING, logger=gemini_service.__name__):
        with pytest.raises(gemini_service.GeminiUpstreamError) as caught:
            asyncio.run(gemini_service.generate_text('system', 'PRIVATE_PROMPT'))
    error = caught.value
    assert (error.status_code, error.upstream_status, error.reason) == (
        403, 'PERMISSION_DENIED', 'API_KEY_SERVICE_BLOCKED')
    records = [r for r in caplog.records if r.name == gemini_service.__name__]
    assert len(records) == 1
    assert records[0].getMessage() == (
        'status_code=403 upstream_status=PERMISSION_DENIED reason=API_KEY_SERVICE_BLOCKED')
    assert records[0].exc_info is None
    for secret in ('TEST_KEY_SENTINEL', 'PRIVATE_BODY', 'PRIVATE_PROMPT'):
        assert secret not in caplog.text + str(error)


def test_403_api_response_remains_sanitized(mock_google, monkeypatch):
    mock_google(forbidden)
    database = SimpleNamespace(query=lambda *args: SimpleNamespace(
        filter=lambda *args: SimpleNamespace(first=lambda: object())))
    previous = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = lambda: database
    monkeypatch.setattr(ai, 'build_patient_context', lambda *args: {'available': True})
    monkeypatch.setattr(ai, 'build_prompt', lambda *args: 'PRIVATE_PROMPT')
    try:
        response = TestClient(app).post('/api/v1/ai/patient-assistant',
                                       json={'patient_id': 'mock', 'message': 'test'})
        assert response.status_code == 502
        assert response.json() == {'detail': {
            'error': 'gemini_upstream_error', 'message': 'Gemini upstream request failed.'}}
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


@pytest.mark.parametrize('payload', [
    {'error': {'status': 'TEST_KEY_SENTINEL', 'details': [{'reason': 'TEST_KEY_SENTINEL'}]}},
    {'error': {'status': 'PRIVATE\nBODY', 'details': [{'reason': 'PRIVATE PROMPT'}]}},
    {'error': {'status': {}, 'details': 'PRIVATE_BODY'}},
    [],
])
def test_untrusted_error_fields_not_logged(mock_google, caplog, payload):
    mock_google(lambda request: httpx.Response(403, json=payload))
    with caplog.at_level(logging.WARNING, logger=gemini_service.__name__):
        with pytest.raises(gemini_service.GeminiUpstreamError) as caught:
            asyncio.run(gemini_service.generate_text('system', 'prompt'))
    assert caught.value.status_code == 403
    assert caught.value.upstream_status is None
    assert caught.value.reason is None
    assert 'status_code=403 upstream_status=None reason=None' in caplog.text
    assert 'PRIVATE' not in caplog.text
    assert 'TEST_KEY_SENTINEL' not in caplog.text


def test_network_timeout_is_sanitized(mock_google, caplog):
    def handler(request):
        raise httpx.ReadTimeout('TEST_KEY_SENTINEL PRIVATE_PROMPT', request=request)

    mock_google(handler)
    with caplog.at_level(logging.WARNING, logger=gemini_service.__name__):
        with pytest.raises(gemini_service.GeminiUpstreamError) as caught:
            asyncio.run(gemini_service.generate_text('system', 'prompt'))
    assert caught.value.status_code is None
    assert caught.value.upstream_status is None
    assert caught.value.reason == 'READ_TIMEOUT'
    assert caught.value.__suppress_context__
    assert 'TEST_KEY_SENTINEL' not in caplog.text + str(caught.value)
    assert len([r for r in caplog.records if r.name == gemini_service.__name__]) == 1


def test_non_json_error_preserves_http_status(mock_google):
    mock_google(lambda request: httpx.Response(502, text='PRIVATE_BODY'))
    with pytest.raises(gemini_service.GeminiUpstreamError) as caught:
        asyncio.run(gemini_service.generate_text('system', 'prompt'))
    assert caught.value.status_code == 502
    assert caught.value.upstream_status is None
    assert caught.value.reason is None


def test_empty_success_has_safe_reason(mock_google):
    mock_google(lambda request: httpx.Response(200, json={'candidates': []}))
    with pytest.raises(gemini_service.GeminiUpstreamError) as caught:
        asyncio.run(gemini_service.generate_text('system', 'prompt'))
    assert caught.value.status_code == 200
    assert caught.value.reason == 'NO_USABLE_TEXT'
