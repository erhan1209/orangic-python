# KALISIN Python

Python client for the Cosinner API. Publishing the PyPI project and renaming the repository are separate release steps.

```bash
pip install kalisin
```

```python
from kalisin import Kalisin

# Reads KALISIN_API_KEY. No credentials belong in source files.
with Kalisin() as client:
    response = client.chat.completions.create(
        model="cosinner-2.5",
        reasoning_effort="high",
        messages=[{"role": "user", "content": "Review this function."}],
    )
    print(response.choices[0].message.content)
```

## Configuration

The default API root is `https://api.cosinner.com`. Set `KALISIN_BASE_URL` or pass `base_url` to use a different gateway. Both root and `/v1` base URLs are accepted. Set `KALISIN_API_KEY` or pass `api_key` explicitly.

Cosinner 2.5 accepts `low`, `medium`, `high`, `xhigh`, and `max`. The protocol also accepts `none` to disable thinking where supported. Other model availability comes from `client.models.list()`; this SDK does not imply public access to Sundown.

## Streaming

```python
with Kalisin() as client:
    for event in client.chat.completions.create(
        model="cosinner-2.5",
        messages=[{"role": "user", "content": "Explain this change."}],
        stream=True,
    ):
        if event.get("choices"):
            print(event.choices[0].get("delta", {}).get("content", ""), end="")
```

Response objects support both attributes and dictionaries, including existing code such as `response.choices[0].message["content"]`. Streaming preserves tool-call and reasoning fields instead of converting them to text.

## Errors and retries

Catch `AuthenticationError`, `RateLimitError`, or `APIError`. Errors include `status_code` and `request_id` where the server provides them. Invalid JSON or SSE data raises an error rather than silently dropping output.

The default timeout is 600 seconds. `max_retries` defaults to zero. A positive value retries eligible GET failures only. Generation requests are never automatically replayed because the gateway has no verified idempotency contract and replay could duplicate work or charges.

## Other SDKs

- OpenAI SDK: `base_url="https://api.cosinner.com/v1/openai"`.
- Anthropic SDK: `base_url="https://api.cosinner.com"`.
- KALISIN SDK: `base_url="https://api.cosinner.com"`.

The KALISIN client uses `/v1/chat/completions`. It does not advertise a Responses API that the gateway does not implement.

## Development

```bash
python -m pip install -e ".[dev]"
python -m pytest tests/test_kalisin_client.py
python -m build
```

## Account reports

```python
with Kalisin() as client:
    print(client.balance().balance_usd)
    print(client.pricing())
    print(client.usage(days=30).totals)
```

The gateway provides account reports; they are not inference-server endpoints.
