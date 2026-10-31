import json
import httpx
import pytest
from kalisin import Kalisin, AuthenticationError, APIError, RateLimitError


@pytest.fixture(autouse=True)
def isolated_credentials(monkeypatch):
    for name in ["KALISIN_API_KEY", "COSINNER_API_KEY", "ORANGIC_API_KEY", "KALISIN_BASE_URL"]:
        monkeypatch.delenv(name, raising=False)


def client(handler, **kwargs):
    return Kalisin(api_key="test-only", http_client=httpx.Client(transport=httpx.MockTransport(handler)), **kwargs)


def test_chat_contract_and_response_access():
    def handle(request):
        assert str(request.url) == "https://api.cosinner.com/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer test-only"
        payload = json.loads(request.content)
        assert payload["model"] == "cosinner-2.5" and payload["reasoning_effort"] == "xhigh"
        return httpx.Response(200, json={"choices": [{"message": {"content": "OK"}}]})
    response = client(handle).chat.completions.create(model="cosinner-2.5", reasoning_effort="xhigh", messages=[{"role": "user", "content": "Hi"}])
    assert response.choices[0].message.content == response.choices[0].message["content"] == "OK"


def test_base_url_v1_is_not_duplicated():
    def handle(request):
        assert request.url.path == "/endpoint/v1/models"
        return httpx.Response(200, json={"data": []})
    client(handle, base_url="http://localhost/endpoint/v1/").models.list()


def test_environment_key(monkeypatch):
    monkeypatch.setenv("KALISIN_API_KEY", "test-key")
    with Kalisin() as instance:
        assert instance.api_key == "test-key"
        assert instance.base_url == "https://api.cosinner.com"


def test_missing_credentials():
    with pytest.raises(AuthenticationError):
        Kalisin()


@pytest.mark.parametrize("status,payload,error", [(401, {"detail": "No key"}, AuthenticationError), (429, {"error": "Slow down"}, RateLimitError), (503, {"error": {"message": "Unavailable"}}, APIError)])
def test_error_shapes(status, payload, error):
    instance = client(lambda _: httpx.Response(status, json=payload, headers={"x-request-id": "test-request"}))
    with pytest.raises(error) as caught:
        instance.models.list()
    assert caught.value.status_code == status and caught.value.request_id == "test-request"


def test_stream_preserves_delta_fields_and_ignores_keepalive():
    body = ': heartbeat\n\nevent: message\ndata: {"choices":[{"delta":{"content":"Hi","tool_calls":[{"id":"test-tool"}]}}]}\n\ndata: [DONE]\n\n'
    instance = client(lambda _: httpx.Response(200, text=body, headers={"content-type": "text/event-stream"}))
    chunks = list(instance.chat.completions.create(model="cosinner-2.5", messages=[], stream=True))
    assert len(chunks) == 1
    assert chunks[0].choices[0].delta.tool_calls[0].id == "test-tool"


def test_invalid_stream_does_not_silently_disappear():
    instance = client(lambda _: httpx.Response(200, text="data: broken-json\n\n"))
    with pytest.raises(APIError):
        list(instance.chat.completions.create(model="cosinner-2.5", messages=[], stream=True))


def test_generation_is_not_retried_even_when_get_retries_enabled():
    calls = []
    def handle(request):
        calls.append(request)
        return httpx.Response(503, json={"detail": "Unavailable"})
    with pytest.raises(APIError):
        client(handle, max_retries=2).chat.completions.create(model="cosinner-2.5", messages=[])
    assert len(calls) == 1


def test_model_lookup_uses_available_list_endpoint():
    instance = client(lambda r: httpx.Response(200, json={"data": [{"id": "cosinner-2.5"}]}))
    assert instance.models.retrieve("cosinner-2.5").id == "cosinner-2.5"


def test_reporting_routes_and_days_validation():
    seen = []
    def handler(request):
        seen.append(str(request.url))
        return httpx.Response(200, json={"balance_usd": 10, "totals": {"total_tokens": 12}})
    with httpx.Client(transport=httpx.MockTransport(handler)) as transport:
        with Kalisin(api_key="test", http_client=transport) as client:
            assert client.balance().balance_usd == 10
            client.pricing()
            assert client.usage(days=7).totals.total_tokens == 12
            with pytest.raises(ValueError):
                client.usage(days=366)
    assert seen == ["https://api.cosinner.com/v1/balance", "https://api.cosinner.com/v1/report/pricing", "https://api.cosinner.com/v1/report/usage?days=7"]
