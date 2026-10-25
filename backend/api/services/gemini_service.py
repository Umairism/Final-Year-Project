import logging
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
    if (isinstance(value, str) and re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", value)
            and key not in value):
        return value
    return None


def _upstream_error(*, status_code=None, upstream_status=None, reason=None):
    logger.warning("status_code=%s upstream_status=%s reason=%s",
                   status_code, upstream_status, reason)
    return GeminiUpstreamError(status_code=status_code,
                               upstream_status=upstream_status, reason=reason)


async def generate_text(system_prompt, user_prompt, *, max_output_tokens=512, temperature=0.2):
    settings = get_settings()
    key = settings.GEMINI_API_KEY
    if not key:
        raise GeminiNotConfiguredError()
    url = f'https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent'
    body = {
        'system_instruction': {'parts': [{'text': system_prompt}]},
        'contents': [{'role': 'user', 'parts': [{'text': user_prompt}]}],
        'generationConfig': {'maxOutputTokens': max_output_tokens, 'temperature': temperature},
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, json=body, headers={'x-goog-api-key': key})
    except Exception as exc:
        reason = "READ_TIMEOUT" if isinstance(exc, httpx.ReadTimeout) else "REQUEST_FAILED"
        raise _upstream_error(reason=reason) from None
    if response.status_code >= 400:
        upstream_status = reason = None
        try:
            error = response.json().get('error', {})
            if isinstance(error, dict):
                upstream_status = _safe_code(error.get('status'), key)
                details = error.get('details', [])
                if isinstance(details, list):
                    reason = next((code for detail in details if isinstance(detail, dict)
                                   if (code := _safe_code(detail.get('reason'), key))), None)
        except (ValueError, AttributeError):
            pass
        raise _upstream_error(status_code=response.status_code,
                              upstream_status=upstream_status, reason=reason)
    try:
        text = response.json()['candidates'][0]['content']['parts'][0]['text']
        if not text:
            raise ValueError("No text")
    except Exception:
        raise _upstream_error(status_code=response.status_code, reason="NO_USABLE_TEXT") from None
    return text
