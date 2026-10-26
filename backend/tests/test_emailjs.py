import pytest
import httpx

from api.config import Settings, get_settings
from api.services import auth_service


class FakeResponse:
    def __init__(self, status_code=200, text="ok"):
        self.status_code = status_code
        self.text = text


class FakeClient:
    response = FakeResponse()
    calls = []

    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def post(self, url, json):
        self.calls.append((url, json, self.kwargs))
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def configure(monkeypatch, **values):
    settings = get_settings()
    defaults = {
        "EMAILJS_SERVICE_ID": "service",
        "EMAILJS_TEMPLATE_ID": "template",
        "EMAILJS_PUBLIC_KEY": "public",
        "EMAILJS_PRIVATE_KEY": "private",
        "EMAILJS_API_URL": "https://email.test/send",
        "EMAILJS_TIMEOUT_SECONDS": 15,
        "MAIL_SERVER": None, "MAIL_USERNAME": None, "MAIL_PASSWORD": None, "MAIL_DEFAULT_SENDER": None,
        "ENV": "development",
    }
    defaults.update(values)
    for key, value in defaults.items(): monkeypatch.setattr(settings, key, value)
    return settings


@pytest.mark.asyncio
async def test_emailjs_success_payload(monkeypatch):
    configure(monkeypatch); FakeClient.calls=[]; FakeClient.response=FakeResponse(200); monkeypatch.setattr(auth_service.httpx, "AsyncClient", FakeClient)
    result=await auth_service.send_verification_email("a@example.com", "raw-token")
    assert result == {"mode":"emailjs","sent":True}; url,payload,kwargs=FakeClient.calls[-1]
    assert url == "https://email.test/send" and kwargs["timeout"] == 15
    assert payload["service_id"] == "service" and payload["template_id"] == "template" and payload["user_id"] == "public" and payload["accessToken"] == "private"
    assert payload["template_params"] == {"to_email":"a@example.com","verification_link":"http://localhost:8080/verify-email?token=raw-token","expires_hours":24}


@pytest.mark.asyncio
@pytest.mark.parametrize("response", [FakeResponse(403, "denied"), FakeResponse(500, "failed"), httpx.ReadTimeout("timeout")])
async def test_emailjs_failures_are_safe(monkeypatch, response, caplog):
    configure(monkeypatch); FakeClient.calls=[]; FakeClient.response=response; monkeypatch.setattr(auth_service.httpx, "AsyncClient", FakeClient)
    with pytest.raises(RuntimeError, match="EmailJS delivery failed") as exc:
        await auth_service.send_verification_email("a@example.com", "raw-token")
    text=caplog.text + str(exc.value); assert "private" not in text and "raw-token" not in text and "verification_link" not in text


@pytest.mark.asyncio
async def test_partial_emailjs_names_missing(monkeypatch):
    configure(monkeypatch, EMAILJS_PRIVATE_KEY=None)
    with pytest.raises(RuntimeError, match="EMAILJS_PRIVATE_KEY"):
        await auth_service.send_verification_email("a@example.com", "raw-token")


@pytest.mark.asyncio
async def test_smtp_and_dev_log_fallbacks(monkeypatch):
    configure(monkeypatch, EMAILJS_SERVICE_ID=None, EMAILJS_TEMPLATE_ID=None, EMAILJS_PUBLIC_KEY=None, EMAILJS_PRIVATE_KEY=None, MAIL_SERVER=None)
    assert (await auth_service.send_verification_email("a@example.com", "raw-token"))["mode"] == "dev_log"
    configure(monkeypatch, EMAILJS_SERVICE_ID=None, EMAILJS_TEMPLATE_ID=None, EMAILJS_PUBLIC_KEY=None, EMAILJS_PRIVATE_KEY=None, MAIL_SERVER="smtp", MAIL_USERNAME="u", MAIL_PASSWORD="p", MAIL_DEFAULT_SENDER="s")
    monkeypatch.setattr(auth_service, "_smtp_send", lambda email, link: None)
    assert (await auth_service.send_verification_email("a@example.com", "raw-token"))["mode"] == "smtp"


def test_emailjs_aliases_load_into_canonical_fields(monkeypatch):
    fresh=Settings(_env_file=None, EMAILJS_USER_ID="alias-public", EMAILJS_ACCESS_TOKEN="alias-private")
    assert fresh.EMAILJS_PUBLIC_KEY == "alias-public" and fresh.EMAILJS_PRIVATE_KEY == "alias-private"
