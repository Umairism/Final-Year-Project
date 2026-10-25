import logging
import json
import re

import httpx

from api.config import get_settings

logger = logging.getLogger(__name__)


class GeminiNotConfiguredError(Exception):
    pass


class GeminiUpstreamError(Exception):
    def __init__(self, message="Gemini request failed", *, status_code=None,
                 upstream_status=None, reason=None):
        super().__init__(message)
        self.status_code = status_code
        self.upstream_status = upstream_status
        self.reason = reason


def _safe_code(value, key):
    """Only bounded status identifiers, never free text or credential values."""
    if (isinstance(value, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}", value)
            and key not in value):
        return value
    return None


def _upstream_error(*, status_code=None, upstream_status=None, reason=None, metadata=None):
    if metadata is None:
        logger.warning("status_code=%s upstream_status=%s reason=%s",
                       status_code, upstream_status, reason)
    else:
        logger.warning("status_code=%s upstream_status=%s reason=%s metadata=%s",
                       status_code, upstream_status, reason, json.dumps(metadata, sort_keys=True))
    return GeminiUpstreamError(status_code=status_code,
                               upstream_status=upstream_status, reason=reason)


def _response_metadata(data):
    """Allowlisted structure and numeric usage only; never arbitrary API text."""
    data = data if isinstance(data, dict) else {}
    statuses = {'completed', 'in_progress', 'requires_action', 'failed', 'cancelled', 'canceled', 'expired'}
    types = {'model_output', 'user_input', 'thought', 'text', 'image', 'audio', 'video',
             'tool_call', 'tool_result', 'function_call', 'function_result'}
    status = data.get('status')
    steps = data.get('steps')
    steps = steps if isinstance(steps, list) else []
    step_types, content_types = [], []
    for step in steps:
        if not isinstance(step, dict):
            continue
        kind = step.get('type')
        step_types.append(kind if isinstance(kind, str) and kind in types else 'other')
        content = step.get('content')
        for item in content if isinstance(content, list) else []:
            if isinstance(item, dict):
                kind = item.get('type')
                content_types.append(kind if isinstance(kind, str) and kind in types else 'other')
    usage = data.get('usage')
    usage = usage if isinstance(usage, dict) else {}
    token_fields = ('total_input_tokens', 'total_output_tokens', 'total_thought_tokens',
                    'total_tokens', 'input_tokens', 'output_tokens', 'thinking_tokens',
                    'total_cached_tokens', 'total_tool_use_tokens')
    counts = {name: usage[name] for name in token_fields
              if type(usage.get(name)) is int and usage[name] >= 0}
    return {'interaction_status': status if isinstance(status, str) and status in statuses else 'other',
            'step_types': step_types[:100], 'content_types': content_types[:100], 'usage': counts}


def _extract_text(data):
    """Collect only final model text; never echo user inputs or thoughts."""
    if not isinstance(data, dict):
        return ""
    output_text = data.get('output_text')
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()
    steps = data.get('steps')
    if not isinstance(steps, list):
        return ""
    texts = []
    for step in steps:
        if not isinstance(step, dict) or step.get('type') != 'model_output':
            continue
        content = step.get('content')
        if not isinstance(content, list):
            continue
        for item in content:
            if isinstance(item, dict) and item.get('type') == 'text':
                text = item.get('text')
                if isinstance(text, str):
                    texts.append(text)
    return ''.join(texts).strip()


async def generate_text(system_prompt, user_prompt, *, max_output_tokens=512, temperature=0.2):
    """Generate text without server-side storage using Interactions.

    ``temperature`` is retained for caller compatibility but is not sent;
    Interactions uses the configured ``thinking_level`` instead.
    Its output budget includes thinking tokens. Reserve a minimum budget so
    short requests do not exhaust it before producing visible answer text.
    """
    settings = get_settings()
    key = settings.GEMINI_API_KEY
    if not key:
        raise GeminiNotConfiguredError()
    url = 'https://generativelanguage.googleapis.com/v1beta/interactions'
    body = {
        'model': settings.GEMINI_MODEL,
        'input': user_prompt,
        'generation_config': {
            'max_output_tokens': max(max_output_tokens, settings.GEMINI_MIN_OUTPUT_TOKENS),
            'thinking_level': settings.GEMINI_THINKING_LEVEL,
            'thinking_summaries': 'none',
        },
        'store': False,
        'stream': False,
    }
    if system_prompt:
        body['system_instruction'] = system_prompt
    timeout = httpx.Timeout(
        connect=settings.GEMINI_CONNECT_TIMEOUT_SECONDS,
        read=settings.GEMINI_READ_TIMEOUT_SECONDS,
        write=settings.GEMINI_WRITE_TIMEOUT_SECONDS,
        pool=settings.GEMINI_POOL_TIMEOUT_SECONDS,
    )
    headers = {'x-goog-api-key': key, 'Content-Type': 'application/json',
               'Api-Revision': '2026-05-20'}
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=body, headers=headers)
    except httpx.TimeoutException:
        raise _upstream_error(reason="timeout") from None
    except httpx.RequestError:
        raise _upstream_error(reason="network_error") from None
    if response.status_code >= 400:
        upstream_status = reason = None
        try:
            error = response.json().get('error', {})
            if isinstance(error, dict):
                upstream_status = (_safe_code(error.get('status'), key)
                                   or _safe_code(error.get('code'), key))
                details = error.get('details', [])
                if isinstance(details, list):
                    reason = next((code for detail in details if isinstance(detail, dict)
                                   if (code := _safe_code(detail.get('reason'), key))), None)
        except (ValueError, AttributeError):
            pass
        raise _upstream_error(status_code=response.status_code,
                              upstream_status=upstream_status, reason=reason)
    try:
        data = response.json()
    except ValueError:
        raise _upstream_error(status_code=response.status_code, reason="NO_USABLE_TEXT",
                              metadata=_response_metadata(None)) from None
    if isinstance(data, dict):
        status = data.get('status')
        if isinstance(status, str) and status.lower() in {'failed', 'cancelled', 'canceled', 'expired'}:
            raise _upstream_error(status_code=response.status_code,
                                  upstream_status=status.lower(), reason="INTERACTION_FAILED")
    text = _extract_text(data)
    if not text:
        raise _upstream_error(status_code=response.status_code, reason="NO_USABLE_TEXT",
                              metadata=_response_metadata(data))
    return text
