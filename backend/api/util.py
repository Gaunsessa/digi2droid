import json
import httpx

from typing import Any
from openrouter import OpenRouter

import config


def download_image(url: str, timeout_sec: float = 30.0) -> tuple[bytes, str]:
    headers = {"Accept": "image/*,*/*"}

    with httpx.Client(timeout=timeout_sec, follow_redirects=True) as client:
        with client.stream("GET", url, headers=headers) as resp:
            resp.raise_for_status()
            ctype = resp.headers.get("content-type", "").split(";")[0].strip().lower()
            chunks: list[bytes] = []
            total = 0
            for chunk in resp.iter_bytes():
                total += len(chunk)
                if total > config.MAX_IMAGE_BYTES:
                    raise ValueError(
                        f"Image exceeds max size ({config.MAX_IMAGE_BYTES} bytes)"
                    )
                chunks.append(chunk)

    if not ctype.startswith("image/"):
        ctype = "image/jpeg"
    
    return b"".join(chunks), ctype


def chat(
    messages: list[dict[str, Any]],
    *,
    temperature: float = 0.3,
    max_tokens: int = 200,
) -> str:
    if not config.OPENROUTER_API_KEY or not config.OPENROUTER_MODEL:
        raise RuntimeError("OPENROUTER_API_KEY or OPENROUTER_MODEL is not set")

    with OpenRouter(
        api_key=config.OPENROUTER_API_KEY,
        server_url=config.OPENROUTER_BASE_URL,
    ) as client:
        resp = client.chat.send(
            model=config.OPENROUTER_MODEL,
            messages=messages,  # type: ignore[arg-type]
            temperature=temperature,
            max_tokens=max_tokens,
        )

    content = resp.choices[0].message.content
    if content is None:
        return ""
    
    return str(content).strip()


_RUNPOD_BASE = "https://api.runpod.ai/v2"


def runpod_request(method: str, path: str, **kwargs: Any) -> dict:
    if not config.RUNPOD_API_KEY or not config.RUNPOD_ENDPOINT_ID:
        raise RuntimeError("RUNPOD_API_KEY or RUNPOD_ENDPOINT_ID is not set")

    url = f"{_RUNPOD_BASE}/{config.RUNPOD_ENDPOINT_ID}/{path}"
    headers = {
        "Authorization": f"Bearer {config.RUNPOD_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    with httpx.Client(timeout=60.0) as client:
        r = client.request(method, url, headers=headers, **kwargs)
        r.raise_for_status()
        return r.json()


def normalize_runpod_output(raw: Any) -> dict:
    out = raw

    if isinstance(out, str):
        out = json.loads(out)
    
    if isinstance(out, list) and len(out) == 1:
        out = out[0]
    
    if not isinstance(out, dict):
        raise RuntimeError(f"RunPod output has unexpected shape: {raw!r}")
    
    return out


def image_url_from_result(item: dict) -> str | None:
    url = item.get("original") or item.get("thumbnail") or item.get("image")

    if isinstance(url, str) and url.startswith("http"):
        return url
    
    return None
