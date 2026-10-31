"""Synchronous Cosinner client with streaming and a reusable HTTP connection."""
import json
import os
import time
from typing import Any, Dict, Iterator, Optional

import httpx

__version__ = "0.2.0"
EFFORTS = {"none", "low", "medium", "high", "xhigh", "max"}


class KalisinError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None, request_id: Optional[str] = None):
        super().__init__(message)
        self.message, self.status_code, self.request_id = message, status_code, request_id


class APIError(KalisinError):
    pass


class AuthenticationError(KalisinError):
    pass


class RateLimitError(KalisinError):
    pass


class Record(dict):
    """Responses support attribute and dictionary access."""
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError as exc:
            raise AttributeError(key) from exc


def record(value):
    if isinstance(value, dict):
        return Record({key: record(item) for key, item in value.items()})
    if isinstance(value, list):
        return [record(item) for item in value]
    return value


class Message:
    def __init__(self, role: str, content: Any):
        self.role, self.content = role, content

    def to_dict(self):
        return {"role": self.role, "content": self.content}


class Completions:
    def __init__(self, client):
        self.client = client

    def create(self, *, model: str, messages, stream: bool = False, reasoning_effort: Optional[str] = None, **kwargs):
        if reasoning_effort is not None and reasoning_effort not in EFFORTS:
            raise ValueError("reasoning_effort must be low, medium, high, xhigh, or max")
        payload = {"model": model, "messages": [m.to_dict() if isinstance(m, Message) else m for m in messages], "stream": stream}
        payload.update({k: v for k, v in kwargs.items() if v is not None})
        if reasoning_effort is not None:
            payload["reasoning_effort"] = reasoning_effort
        if stream:
            return self.client._stream("/v1/chat/completions", payload)
        return self.client._request("POST", "/v1/chat/completions", json=payload)


class Chat:
    def __init__(self, client):
        self.completions = Completions(client)


class Models:
    def __init__(self, client):
        self.client = client

    def list(self):
        return self.client._request("GET", "/v1/models")

    def retrieve(self, model):
        # The gateway only exposes a list endpoint; do not advertise an unsupported route.
        for item in self.list().get("data", []):
            if item.get("id") == model:
                return item
        raise APIError("Model not found: " + model, 404)


class Kalisin:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None,
                 timeout: float = 600.0, max_retries: int = 0, http_client: Optional[httpx.Client] = None):
        self.api_key = api_key or os.getenv("KALISIN_API_KEY")
        if not self.api_key:
            raise AuthenticationError("Set KALISIN_API_KEY or pass api_key.")
        self.base_url = (base_url or os.getenv("KALISIN_BASE_URL") or "https://api.cosinner.com").rstrip("/")
        if self.base_url.endswith("/v1"):
            self.base_url = self.base_url[:-3]
        if not isinstance(max_retries, int) or not 0 <= max_retries <= 5:
            raise ValueError("max_retries must be an integer between 0 and 5")
        self.timeout, self.max_retries = timeout, max_retries
        self._owned_client = http_client is None
        self._http = http_client or httpx.Client(timeout=timeout)
        self.chat, self.models = Chat(self), Models(self)

    def balance(self):
        return self._request("GET", "/v1/balance")

    def pricing(self):
        return self._request("GET", "/v1/report/pricing")

    def usage(self, days=30):
        if not isinstance(days, int) or isinstance(days, bool) or not 1 <= days <= 365:
            raise ValueError("days must be an integer between 1 and 365")
        return self._request("GET", "/v1/report/usage", params={"days": days})

    def _headers(self):
        return {"Authorization": "Bearer " + self.api_key, "Content-Type": "application/json", "User-Agent": "kalisin-python/" + __version__}

    def _handle_error(self, response):
        if 200 <= response.status_code < 300:
            return
        try:
            data = response.json()
            error = data.get("error", data.get("detail", data))
            message = error.get("message", str(error)) if isinstance(error, dict) else str(error)
        except (ValueError, AttributeError):
            message = response.text or "API request failed"
        error_type = AuthenticationError if response.status_code == 401 else RateLimitError if response.status_code == 429 else APIError
        raise error_type(message, response.status_code, response.headers.get("x-request-id"))

    def _request(self, method, path, **kwargs):
        # Only GET retries are safe without a server-supported idempotency contract.
        attempts = self.max_retries + 1 if method == "GET" else 1
        for attempt in range(attempts):
            response = self._http.request(method, self.base_url + path, headers=self._headers(), timeout=self.timeout, **kwargs)
            if attempt + 1 < attempts and response.status_code in {429, 500, 502, 503, 504}:
                response.close()
                time.sleep(min(0.25 * (2 ** attempt), 2))
                continue
            self._handle_error(response)
            if response.status_code == 204:
                return None
            try:
                return record(response.json())
            except ValueError as exc:
                raise APIError("API returned invalid JSON", response.status_code) from exc

    def _stream(self, path, payload) -> Iterator[Record]:
        with self._http.stream("POST", self.base_url + path, headers=self._headers(), json=payload, timeout=self.timeout) as response:
            if response.is_error:
                response.read()
                self._handle_error(response)
            event = []
            for line in response.iter_lines():
                if line.startswith("data:"):
                    event.append(line[5:].lstrip(" "))
                elif not line and event:
                    data = "\n".join(event)
                    event = []
                    if data.strip() == "[DONE]":
                        return
                    yield self._chunk(data)
            if event and "\n".join(event).strip() != "[DONE]":
                yield self._chunk("\n".join(event))

    @staticmethod
    def _chunk(data):
        try:
            chunk = json.loads(data)
        except ValueError as exc:
            raise APIError("API returned an invalid streaming event") from exc
        if isinstance(chunk, dict) and chunk.get("error"):
            raise APIError(str(chunk["error"]))
        return record(chunk)

    def close(self):
        if self._owned_client:
            self._http.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


def completion(model, messages, api_key=None, **kwargs):
    if kwargs.get("stream"):
        raise ValueError("Use Kalisin as a context manager for streaming.")
    with Kalisin(api_key=api_key) as client:
        return client.chat.completions.create(model=model, messages=messages, **kwargs)
