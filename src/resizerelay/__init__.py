"""Official Python SDK for the Resize Relay API.

Resize images to exact KB file sizes and exact pixel dimensions — the specs
passport portals, government exam forms, and marketplaces actually enforce.

Docs: https://www.resizerelay.com/api-docs
Keys: https://www.resizerelay.com/dashboard/api-keys
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import BinaryIO, Optional, Union

import requests

__all__ = ["ResizeRelay", "ResizeRelayError", "ResizeResult"]
__version__ = "0.1.0"

DEFAULT_BASE_URL = "https://www.resizerelay.com"

_MIME_BY_FORMAT = {
    "jpeg": "image/jpeg",
    "jpg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
    "image/jpeg": "image/jpeg",
    "image/png": "image/png",
    "image/webp": "image/webp",
}

ImageInput = Union[str, bytes, BinaryIO]


class ResizeRelayError(Exception):
    """Raised for any non-2xx API response.

    Attributes:
        status: HTTP status (401 invalid key, 429 rate/quota, 400 bad input…).
        request_id: Server request id — include it when contacting support.
        retry_after: Seconds to wait before retrying (set on burst rate limits).
    """

    def __init__(
        self,
        message: str,
        status: Optional[int] = None,
        request_id: Optional[str] = None,
        retry_after: Optional[int] = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.request_id = request_id
        self.retry_after = retry_after


@dataclass
class ResizeResult:
    """The resized image plus request metadata."""

    content: bytes
    content_type: str
    request_id: Optional[str]
    quota_limit: Optional[int]
    quota_used: Optional[int]
    quota_remaining: Optional[int]

    def save(self, path: str) -> None:
        """Write the resized image to disk."""
        with open(path, "wb") as handle:
            handle.write(self.content)


def _header_int(response: requests.Response, name: str) -> Optional[int]:
    value = response.headers.get(name)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


class ResizeRelay:
    """Client for the Resize Relay API.

    Example:
        >>> client = ResizeRelay(os.environ["RESIZERELAY_API_KEY"])
        >>> result = client.resize(
        ...     "photo.jpg", target_kb=100, width=600, height=600, fit="cover"
        ... )
        >>> result.save("photo-600.jpg")
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 60.0,
        session: Optional[requests.Session] = None,
    ) -> None:
        if not api_key or not isinstance(api_key, str):
            raise TypeError(
                "ResizeRelay: an API key is required. Create one at "
                "https://www.resizerelay.com/dashboard/api-keys"
            )
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = session or requests.Session()

    def resize(
        self,
        image: ImageInput,
        *,
        target_kb: Optional[float] = None,
        target_mb: Optional[float] = None,
        min_kb: Optional[float] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        fit: Optional[str] = None,
        format: Optional[str] = None,
        quality: Optional[float] = None,
        filename: Optional[str] = None,
    ) -> ResizeResult:
        """Resize an image to an exact file size and/or exact dimensions.

        Args:
            image: A file path, raw bytes, or a binary file-like object.
            target_kb: Max output size in KB (e.g. 100).
            target_mb: Max output size in MB (overrides target_kb).
            min_kb: Min output size in KB — compliance bands like "20–50 KB".
            width: Output width in px.
            height: Output height in px.
            fit: "cover" crops (centered, saliency-aware) to exactly
                width×height; "inside" fits within, preserving aspect (default).
            format: Output format — "jpeg" (default), "png", or "webp".
            quality: Encoder quality 0–1 (default 0.92). Ignored for png.
            filename: Filename hint sent with the upload.
        """
        if isinstance(image, str):
            name = filename or os.path.basename(image)
            with open(image, "rb") as handle:
                payload = handle.read()
        elif isinstance(image, (bytes, bytearray)):
            name = filename or "image"
            payload = bytes(image)
        elif hasattr(image, "read"):
            name = filename or getattr(image, "name", None) or "image"
            payload = image.read()
        else:
            raise TypeError(
                "Unsupported image input — pass a file path, bytes, or a "
                "binary file-like object."
            )

        data: dict[str, str] = {}
        if target_mb is not None:
            data["targetValue"] = str(target_mb)
            data["targetUnit"] = "MB"
        elif target_kb is not None:
            data["targetValue"] = str(target_kb)
            data["targetUnit"] = "KB"
        if width is not None:
            data["width"] = str(width)
        if height is not None:
            data["height"] = str(height)
        if fit is not None:
            if fit not in ("cover", "inside"):
                raise ValueError('fit must be "cover" or "inside".')
            data["fit"] = fit
        if format is not None:
            mime = _MIME_BY_FORMAT.get(format.lower())
            if mime is None:
                raise ValueError(
                    f'Unsupported format "{format}" — use "jpeg", "png", or "webp".'
                )
            data["format"] = mime
        if quality is not None:
            data["quality"] = str(quality)
        if min_kb is not None:
            data["minBytes"] = str(round(min_kb * 1000))

        try:
            response = self._session.post(
                f"{self.base_url}/api/v1/resize",
                headers={"authorization": f"Bearer {self.api_key}"},
                files={"file": (name, payload)},
                data=data,
                timeout=self.timeout,
            )
        except requests.RequestException as cause:
            raise ResizeRelayError(f"Network error calling Resize Relay: {cause}") from cause

        request_id = response.headers.get("x-request-id")

        if not response.ok:
            message = f"Resize failed with HTTP {response.status_code}."
            try:
                body = response.json()
                if isinstance(body, dict) and isinstance(body.get("error"), str):
                    message = body["error"]
            except ValueError:
                pass
            raise ResizeRelayError(
                message,
                status=response.status_code,
                request_id=request_id,
                retry_after=_header_int(response, "retry-after"),
            )

        return ResizeResult(
            content=response.content,
            content_type=response.headers.get("content-type", "application/octet-stream"),
            request_id=request_id,
            quota_limit=_header_int(response, "x-quota-limit"),
            quota_used=_header_int(response, "x-quota-used"),
            quota_remaining=_header_int(response, "x-quota-remaining"),
        )

    def resize_to_file(self, image: ImageInput, output_path: str, **options) -> ResizeResult:
        """Resize and write the result straight to disk. Same options as resize()."""
        result = self.resize(image, **options)
        result.save(output_path)
        return result
