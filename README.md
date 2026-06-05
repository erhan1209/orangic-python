# Orangic Python SDK

The official Python library for the Orangic API.

## Installation

```bash
pip install orangic
```

## Quick Start

```python
import orangic

client = orangic.Orangic(api_key="your-api-key")

response = client.chat.completions.create(
    model="org-2",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the capital of France?"}
    ]
)

print(response.content)
```

## Configuration

### API Key

Set your API key in one of two ways:

1. **Environment variable** (recommended):
```bash
export ORANGIC_API_KEY='your-api-key'
```

2. **Direct initialization**:
```python
client = orangic.Orangic(api_key="your-api-key")
```

### Custom Base URL

```python
client = orangic.Orangic(
    api_key="your-api-key",
    base_url="https://myapi.example.com"
)
```


## Usage Examples

### Basic Chat Completion

```python
import orangic

client = orangic.Orangic()

response = client.chat.completions.create(
    model="org-2",
    messages=[
        {"role": "user", "content": "Tell me a joke"}
    ]
)

print(response.content)
```

> **`org-1` is deprecated.** Please migrate to `org-2`.

### Streaming Responses

```python
import orangic

client = orangic.Orangic()

stream = client.chat.completions.create(
    model="org-2",
    messages=[{"role": "user", "content": "Write a story"}],
    stream=True
)

for chunk in stream:
    if chunk.channel == "final" and chunk.content:
        print(chunk.content, end="", flush=True)
```

### Streaming with Reasoning (Narrative Channel)

When `reasoning > 0`, the model may emit `"narrative"` chunks — visible commentary on its thinking process.

```python
stream = client.chat.completions.create(
    model="org-2",
    messages=[{"role": "user", "content": "Solve: if a train leaves at 3pm..."}],
    stream=True,
    reasoning=3  # medium reasoning
)

for chunk in stream:
    if chunk.channel == "narrative":
        print(f"[thinking] {chunk.content}", end="", flush=True)
    elif chunk.channel == "final":
        print(chunk.content, end="", flush=True)
```

### Image Input

ORG-2 supports image inputs including screenshots, photos, charts, diagrams, and mixed-modality documents.

```python
import orangic, base64

with open("screenshot.png", "rb") as f:
    image_data = base64.b64encode(f.read()).decode()

response = client.chat.completions.create(
    model="org-2",
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": image_data
                    }
                },
                {"type": "text", "text": "Summarize the key fields in this form. Return JSON."}
            ]
        }
    ]
)

print(response.content)
```

### Video Input

ORG-2 supports video up to ~30 minutes at ~720p. **Audio is not processed** — pair your video with subtitles or a transcript when spoken content matters.

```python
response = client.chat.completions.create(
    model="org-2",
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "video",
                    "source": {"type": "url", "url": "https://example.com/lecture.mp4"}
                },
                {
                    "type": "text",
                    "text": "Produce: (1) a timeline of sections, (2) key claims, (3) open questions."
                }
            ]
        }
    ]
)

print(response.content)
```

### Using Message Objects

```python
import orangic

client = orangic.Orangic()

messages = [
    orangic.Message(role="system", content="You are a helpful assistant"),
    orangic.Message(role="user", content="Hello!")
]

response = client.chat.completions.create(
    model="org-2",
    messages=messages
)

print(response.content)
```

### Reasoning

The `reasoning` parameter enables the model to think before responding.

> **Note for `org-2`:** Deployments may use a summarizer to return a condensed version of the reasoning rather than the full token-by-token output. The reasoning content you see in the response may not reflect the full reasoning actually performed — and the token count in `usage` will reflect actual tokens used, not the summarized output.

For `org-2`, reasoning is a simple on/off toggle — pass `True`/`1` to enable or `False`/`0` to disable (default).

```python
response = client.chat.completions.create(
    model="org-2",
    messages=[{"role": "user", "content": "A farmer has 17 sheep. All but 9 die. How many are left?"}],
    reasoning=True
)

print(response.content)
```

| Value | Behavior |
|-------|----------|
| `False` / `0` | No reasoning. Fastest. Default. |
| `True` / `1` | Reasoning enabled. |

> **Note:** The multi-level reasoning values (`"low"`, `"medium"`, `"high"`, `2`–`4`) are not supported by `org-2` and will be discarded — see [Deprecated Parameters](#deprecated-parameters).

### Quick Completion (No Client Instance)

```python
import orangic

response = orangic.completion(
    model="org-2",
    messages=[{"role": "user", "content": "Hello"}],
    api_key="your-api-key"
)

print(response.content)
```

## Deprecated Parameters

The following parameters are accepted by the SDK but **silently discarded by the API** for models that do not support them (including `org-2`). To control output style, use prompting and system instructions instead.

| Parameter | Status |
|-----------|--------|
| `temperature` | Discarded for `org-2` |
| `top_p` | Discarded for `org-2` |
| `frequency_penalty` | Discarded for `org-2` |
| `presence_penalty` | Discarded for `org-2` |
| `stop` | Discarded for `org-2` |
| `reasoning` levels (`"low"`, `"medium"`, `"high"`, `2`–`4`) | Discarded for `org-2` — use `True`/`False` instead |

## Error Handling

```python
import orangic

client = orangic.Orangic()

try:
    response = client.chat.completions.create(
        model="org-2",
        messages=[{"role": "user", "content": "Hello"}]
    )
    print(response.content)
except orangic.AuthenticationError as e:
    print(f"Authentication failed: {e}")
except orangic.RateLimitError as e:
    print(f"Rate limit exceeded: {e}")
except orangic.APIError as e:
    print(f"API error {e.status_code}: {e}")
```

## API Reference

### Client Initialization

```python
Orangic(
    api_key: Optional[str] = None,
    base_url: str = "https://api.orangic.chat",
    timeout: float = 600.0,
    max_retries: int = 2
)
```

### Chat Completions

```python
client.chat.completions.create(
    model: str,                              # "org-2"
    messages: List[Dict[str, str]],
    max_tokens: Optional[int] = None,        # up to 256k for org-2
    stream: bool = False,
    reasoning: Optional[bool] = None,         # True/False for org-2; multi-level discarded

    # Deprecated — accepted but discarded for org-2
    temperature: float = 0.7,
    top_p: Optional[float] = None,
    frequency_penalty: float = 0.0,
    presence_penalty: float = 0.0,
    stop: Optional[Union[str, List[str]]] = None,
)
```

### Response Object

```python
response.content        # str — the model's reply
response.id             # str — completion ID
response.model          # str — model used
response.finish_reason  # str — "stop" or "tool_calls"
response.usage          # dict — {"prompt_tokens": ..., "completion_tokens": ..., "total_tokens": ...}
                        # Note: for org-2 with reasoning enabled, completion_tokens reflects actual
                        # reasoning tokens used — not the (possibly summarized) reasoning you can see.
```

### Streaming Chunk

```python
chunk.content   # str — token text
chunk.channel   # str — "final" (response) or "narrative" (thinking commentary)
```

## Requirements

- Python 3.8+
- httpx >= 0.24.0

## License

MIT License

## Support

For support, email support@orangic.chat or visit https://platform.orangic.chat/docs
