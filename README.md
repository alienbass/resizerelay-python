# Resize Relay — Python SDK

[![PyPI version](https://img.shields.io/pypi/v/resizerelay)](https://pypi.org/project/resizerelay/) [![license](https://img.shields.io/pypi/l/resizerelay)](./LICENSE)

Official Python client for the [Resize Relay API](https://www.resizerelay.com/api-docs): resize images to **exact KB file sizes** and **exact pixel dimensions** — the specs that passport portals, government exam forms, and marketplaces actually enforce.

- **Exact-size engine** — binary-searches encoder quality to hit a KB ceiling (and a floor, for "20–50 KB" style bands), reducing resolution only when unavoidable.
- **Exact-dimension crops** — `fit="cover"` produces exactly `width×height` with a centered, saliency-aware crop (no stretching).
- **Free tier** — 500 resizes/month per key. [Create a key →](https://www.resizerelay.com/dashboard/api-keys)

## Install

```bash
pip install resizerelay
```

## Quickstart

```python
import os
from resizerelay import ResizeRelay

client = ResizeRelay(os.environ["RESIZERELAY_API_KEY"])

# Job-portal photo: exactly 600×600, under 100 KB
client.resize_to_file(
    "photo.jpg", "photo-600.jpg",
    target_kb=100, width=600, height=600, fit="cover",
)

# Exam signature: 350×200 JPEG between 10 and 20 KB
result = client.resize(
    "signature.png",
    target_kb=20, min_kb=10, width=350, height=200,
    fit="cover", format="jpeg",
)
print(result.content_type, len(result.content), "bytes")
print("quota:", result.quota_used, "/", result.quota_limit)
```

Input can be a **file path, `bytes`, or a binary file-like object**. `ResizeResult.content` holds the resized image; quota headers are parsed for you.

## Options

| Option      | Type                  | Description |
| ----------- | --------------------- | ----------- |
| `target_kb` | `float`               | Max output size in KB. |
| `target_mb` | `float`               | Max output size in MB (overrides `target_kb`). |
| `min_kb`    | `float`               | Min output size in KB (compliance bands). |
| `width`     | `int`                 | Output width in px. |
| `height`    | `int`                 | Output height in px. |
| `fit`       | `"cover" \| "inside"` | `cover` = exact `width×height` via centered crop; `inside` = fit within, keep aspect (default). |
| `format`    | `"jpeg" \| "png" \| "webp"` | Output format (default `jpeg`). |
| `quality`   | `float`               | Encoder quality `0–1` (default `0.92`). |

## Error handling

All non-2xx responses raise `ResizeRelayError` with `status`, `request_id`, and (for rate limits) `retry_after`:

```python
from resizerelay import ResizeRelay, ResizeRelayError

try:
    client.resize("photo.jpg", target_kb=50)
except ResizeRelayError as err:
    print(err.status, err, "request:", err.request_id)
    if err.status == 429 and err.retry_after:
        ...  # burst limit — back off err.retry_after seconds
```

| Status | Meaning |
| ------ | ------- |
| `400`  | Bad input (missing file, unreachable target). |
| `401`  | Missing, invalid, or revoked API key. |
| `413`  | Image larger than 25 MB. |
| `429`  | Burst rate limit (120 req/min) or monthly quota reached. |

## Links

- [API documentation](https://www.resizerelay.com/api-docs)
- [Get an API key](https://www.resizerelay.com/dashboard/api-keys)
- [Resize Relay](https://www.resizerelay.com) — the free in-browser tools
- [Node.js SDK](https://github.com/alienbass/resizerelay-node)

## License

[MIT](./LICENSE)
