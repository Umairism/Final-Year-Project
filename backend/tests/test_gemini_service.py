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
        GEMINI_API_KEY='TEST_KEY_SENTINEL', GEMINI_MODEL='test-model',
        GEMINI_CONNECT_TIMEOUT_SECONDS=7, GEMINI_READ_TIMEOUT_SECONDS=83,
        GEMINI_WRITE_TIMEOUT_SECONDS=23, GEMINI_POOL_TIMEOUT_SECONDS=9,
        GEMINI_THINKING_LEVEL='low', GEMINI_MIN_OUTPUT_TOKENS=256))
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
        assert str(request.url) == 'https://generativelanguage.googleapis.com/v1beta/interactions'
        assert request.headers['Api-Revision'] == '2026-05-20'
        assert request.headers['Content-Type'] == 'application/json'
        assert request.extensions['timeout'] == {'connect': 7, 'read': 83, 'write': 23, 'pool': 9}
        assert json.loads(request.content) == {
            'model': 'test-model', 'system_instruction': 'system', 'input': 'prompt',
            'generation_config': {'max_output_tokens': 256, 'thinking_level': 'low',
                                  'thinking_summaries': 'none'},
            'store': False, 'stream': False,
        }
        return httpx.Response(200, json={'status': 'completed', 'steps': [
            {'type': 'user_input', 'content': [{'type': 'text', 'text': 'PRIVATE_USER'}]},
            {'type': 'thought', 'content': [{'type': 'text', 'text': 'PRIVATE_THOUGHT'}]},
            {'type': 'model_output', 'content': [
                {'type': 'thought', 'text': 'PRIVATE_THOUGHT'},
                {'type': 'text', 'text': '  O'}, {'type': 'image', 'text': 'PRIVATE_IMAGE'}]},
            {'type': 'model_output', 'content': [{'type': 'text', 'text': 'K  '}]},
        ]})

    mock_google(handler)
    assert asyncio.run(gemini_service.generate_text('system', 'prompt', max_output_tokens=16)) == 'OK'


@pytest.mark.parametrize('status,upstream,reason', [
    (403, 'PERMISSION_DENIED', 'API_KEY_SERVICE_BLOCKED'),
    (503, 'UNAVAILABLE', 'MODEL_OVERLOADED'),
])
def test_http_attributes_and_single_safe_warning(mock_google, caplog, status, upstream, reason):
    mock_google(lambda request: httpx.Response(status, json={'error': {
        'code': status, 'status': upstream,
        'message': 'TEST_KEY_SENTINEL PRIVATE_BODY PRIVATE_PROMPT',
        'details': [{'reason': reason}],
    }}))
    with caplog.at_level(logging.WARNING, logger=gemini_service.__name__):
        with pytest.raises(gemini_service.GeminiUpstreamError) as caught:
            asyncio.run(gemini_service.generate_text('system', 'PRIVATE_PROMPT'))
    error = caught.value
    assert (error.status_code, error.upstream_status, error.reason) == (
        status, upstream, reason)
    records = [r for r in caplog.records if r.name == gemini_service.__name__]
    assert len(records) == 1
    assert records[0].getMessage() == (
        f'status_code={status} upstream_status={upstream} reason={reason}')
    assert records[0].exc_info is None
    for secret in ('TEST_KEY_SENTINEL', 'PRIVATE_BODY', 'PRIVATE_PROMPT'):
        assert secret not in caplog.text + str(error)


@pytest.mark.parametrize('status,upstream', [(403, 'PERMISSION_DENIED'), (503, 'UNAVAILABLE')])
def test_http_api_response_remains_sanitized(mock_google, monkeypatch, status, upstream):
    mock_google(lambda request: httpx.Response(status, json={'error': {
        'code': status, 'status': upstream, 'message': 'TEST_KEY_SENTINEL PRIVATE_BODY',
    }}))
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
        assert request.extensions['timeout']['read'] == 83
        raise httpx.ReadTimeout('TEST_KEY_SENTINEL PRIVATE_PROMPT', request=request)

    mock_google(handler)
    with caplog.at_level(logging.WARNING, logger=gemini_service.__name__):
        with pytest.raises(gemini_service.GeminiUpstreamError) as caught:
            asyncio.run(gemini_service.generate_text('system', 'prompt'))
    assert caught.value.status_code is None
    assert caught.value.upstream_status is None
    assert caught.value.reason == 'timeout'
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
    mock_google(lambda request: httpx.Response(200, json={'steps': []}))
    with pytest.raises(gemini_service.GeminiUpstreamError) as caught:
        asyncio.run(gemini_service.generate_text('system', 'prompt'))
    assert caught.value.status_code == 200
    assert caught.value.reason == 'NO_USABLE_TEXT'


def test_output_text_preferred(mock_google):
    mock_google(lambda request: httpx.Response(200, json={
        'output_text': '  Final answer  ',
        'steps': [{'type': 'model_output', 'content': [{'type': 'text', 'text': 'ignored'}]}],
    }))
    assert asyncio.run(gemini_service.generate_text('system', 'prompt')) == 'Final answer'


def test_blank_output_text_falls_back_to_steps(mock_google):
    mock_google(lambda request: httpx.Response(200, json={
        'output_text': '   ',
        'steps': [{'type': 'model_output', 'content': [{'type': 'text', 'text': 'OK'}]}],
    }))
    assert asyncio.run(gemini_service.generate_text('system', 'prompt')) == 'OK'


@pytest.mark.parametrize('status', ['failed', 'cancelled', 'canceled', 'expired'])
def test_failed_interaction_rejects_even_present_text(mock_google, caplog, status):
    mock_google(lambda request: httpx.Response(200, json={
        'status': status, 'output_text': 'Do not return this',
    }))
    with pytest.raises(gemini_service.GeminiUpstreamError) as caught:
        asyncio.run(gemini_service.generate_text('system', 'prompt'))
    assert caught.value.status_code == 200
    assert caught.value.upstream_status == status
    assert caught.value.reason == 'INTERACTION_FAILED'
    assert len([r for r in caplog.records if r.name == gemini_service.__name__]) == 1


@pytest.mark.parametrize('payload', [
    None, [], {'output_text': 123}, {'steps': 'malformed'},
    {'steps': [None, {'type': 'model_output', 'content': None}]},
    {'steps': [{'type': 'model_output', 'content': [None, {'type': 'text', 'text': {}}]}]},
    {'steps': [{'type': 'user_input', 'content': [{'type': 'text', 'text': 'private'}]}]},
])
def test_malformed_or_non_model_text_rejected(mock_google, payload):
    mock_google(lambda request: httpx.Response(200, content=json.dumps(payload)))
    with pytest.raises(gemini_service.GeminiUpstreamError) as caught:
        asyncio.run(gemini_service.generate_text('system', 'prompt'))
    assert caught.value.reason == 'NO_USABLE_TEXT'


def test_non_json_success_rejected(mock_google):
    mock_google(lambda request: httpx.Response(200, text='PRIVATE_BODY'))
    with pytest.raises(gemini_service.GeminiUpstreamError) as caught:
        asyncio.run(gemini_service.generate_text('system', 'prompt'))
    assert caught.value.reason == 'NO_USABLE_TEXT'


def test_empty_system_prompt_omitted(mock_google):
    def handler(request):
        assert 'system_instruction' not in json.loads(request.content)
        return httpx.Response(200, json={'output_text': 'OK'})

    mock_google(handler)
    assert asyncio.run(gemini_service.generate_text('', 'prompt')) == 'OK'


def test_missing_key_does_not_create_client(monkeypatch):
    monkeypatch.setattr(gemini_service, 'get_settings', lambda: SimpleNamespace(GEMINI_API_KEY=None))

    def forbidden_client(**kwargs):
        pytest.fail('No HTTP client should be created without a key')

    monkeypatch.setattr(gemini_service.httpx, 'AsyncClient', forbidden_client)
    with pytest.raises(gemini_service.GeminiNotConfiguredError):
        asyncio.run(gemini_service.generate_text('system', 'prompt'))


def test_network_error_sanitized(mock_google, caplog):
    def handler(request):
        raise httpx.ConnectError('TEST_KEY_SENTINEL PRIVATE_BODY', request=request)

    mock_google(handler)
    with pytest.raises(gemini_service.GeminiUpstreamError) as caught:
        asyncio.run(gemini_service.generate_text('system', 'prompt'))
    assert caught.value.reason == 'network_error'
    assert 'TEST_KEY_SENTINEL' not in caplog.text + str(caught.value)
    assert len([r for r in caplog.records if r.name == gemini_service.__name__]) == 1


def test_interactions_string_error_code(mock_google):
    mock_google(lambda request: httpx.Response(503, json={
        'error': {'code': 'service_unavailable', 'message': 'PRIVATE_BODY'},
    }))
    with pytest.raises(gemini_service.GeminiUpstreamError) as caught:
        asyncio.run(gemini_service.generate_text('system', 'prompt'))
    assert caught.value.status_code == 503
    assert caught.value.upstream_status == 'service_unavailable'


def test_settings_defaults():
    from api.config import Settings

    defaults = {name: field.default for name, field in Settings.model_fields.items()}
    assert defaults['GEMINI_MODEL'] == 'gemini-3.1-flash-lite'
    assert defaults['GEMINI_CONNECT_TIMEOUT_SECONDS'] == 10
    assert defaults['GEMINI_READ_TIMEOUT_SECONDS'] == 90
    assert defaults['GEMINI_WRITE_TIMEOUT_SECONDS'] == 30
    assert defaults['GEMINI_POOL_TIMEOUT_SECONDS'] == 10
    assert defaults['GEMINI_THINKING_LEVEL'] == 'low'
    assert defaults['GEMINI_MIN_OUTPUT_TOKENS'] == 256


@pytest.mark.parametrize('requested,effective', [(64, 256), (300, 300), (512, 512)])
def test_minimum_output_budget(mock_google, requested, effective):
    def handler(request):
        assert json.loads(request.content)['generation_config']['max_output_tokens'] == effective
        return httpx.Response(200, json={'output_text': 'OK'})

    mock_google(handler)
    assert asyncio.run(gemini_service.generate_text('system', 'prompt', max_output_tokens=requested)) == 'OK'


def test_no_text_metadata_excludes_private_content(mock_google, caplog):
    mock_google(lambda request: httpx.Response(200, json={
        'status': 'completed',
        'steps': [{'type': 'thought', 'content': [{'type': 'text', 'text': 'PRIVATE_PATIENT'}]},
                  {'type': 'PRIVATE_PROMPT', 'content': [{'type': 'TEST_KEY_SENTINEL'}]}],
        'usage': {'total_input_tokens': 20, 'total_output_tokens': 64, 'total_thought_tokens': 64,
                  'PRIVATE_PATIENT': 123, 'total_tokens': 'TEST_KEY_SENTINEL'},
    }))
    with pytest.raises(gemini_service.GeminiUpstreamError):
        asyncio.run(gemini_service.generate_text('PRIVATE_PROMPT', 'PRIVATE_PATIENT'))
    records = [record for record in caplog.records if record.name == gemini_service.__name__]
    assert len(records) == 1
    metadata = json.loads(records[0].getMessage().split('metadata=', 1)[1])
    assert metadata == {'interaction_status': 'completed', 'step_types': ['thought', 'other'],
                        'content_types': ['text', 'other'],
                        'usage': {'total_input_tokens': 20, 'total_output_tokens': 64, 'total_thought_tokens': 64}}
    for secret in ('PRIVATE_PATIENT', 'PRIVATE_PROMPT', 'TEST_KEY_SENTINEL'):
        assert secret not in caplog.text
