import base64
import re
import time
from typing import Any

import serpapi

import config
from util import chat, normalize_runpod_output, runpod_request


# SerpAPI


def google_images_light(query: str, *, api_key: str | None = None) -> list[dict]:
    key = api_key or config.SERPAPI_API_KEY
    if not key:
        raise RuntimeError("SERPAPI_API_KEY is not set")

    client = serpapi.Client(api_key=key)
    try:
        data = client.search(engine="google_images_light", q=query)
    except serpapi.SerpApiError as e:
        raise RuntimeError(str(e)) from e

    if data.get("error"):
        raise RuntimeError(str(data["error"]))

    return list(data.get("images_results") or [])


# OpenRouter


def refine_search_query(camera_name: str) -> str:
    system = (
        "You help build image search queries. Reply with ONLY the search query text, "
        "no quotes or explanation. The query should find clear product photos of the "
        "specific digital camera model. Include brand and model if known. "
        "Prefer English. Keep it under 120 characters."
    )
    text = chat(
        [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": f'Camera name from user or device: "{camera_name}"',
            },
        ]
    )

    line = (text.splitlines()[0] if text else "").strip().strip("\"'")

    return line[:200] if line else camera_name.strip() or "digital camera"


def pick_best_image_index(
    camera_name: str,
    refined_query: str,
    images: list[tuple[bytes, str]],
) -> int:
    n = len(images)
    if n <= 1:
        return 0

    system = (
        "You are an image selection assistant. You will be shown candidate images "
        "from a search for a specific digital camera model. Pick the ONE image that "
        "shows the camera most clearly as a product photo (recognizable body, minimal "
        "occlusion, not a collage or tiny thumbnail). Reply with ONLY a single integer "
        "— the index of the best image."
    )

    user_content: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": (
                f"Camera: {camera_name!r}\n"
                f"Search query: {refined_query!r}\n"
                f"Images 0 to {n - 1} follow. Reply with the best index."
            ),
        }
    ]
    for i, (raw, mime) in enumerate(images):
        b64 = base64.b64encode(raw).decode("ascii")
        user_content.append({"type": "text", "text": f"--- Image {i} ---"})
        user_content.append(
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}
        )

    text = chat(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ],
        temperature=0.2,
        max_tokens=50,
    )

    if m := re.search(r"\d+", text):
        idx = int(m.group())
        if 0 <= idx < n:
            return idx

    return 0


# RunPod


def wait_for_mesh(
    image_base64: str,
    face_count: int,
) -> tuple[str, str]:
    inp: dict[str, Any] = {"image": image_base64, "face_count": face_count}

    data = runpod_request("POST", "run", json={"input": inp})
    job_id = data.get("id")
    if not job_id:
        raise RuntimeError(f"RunPod /run response missing 'id': {data}")
    job_id = str(job_id)

    deadline = time.monotonic() + config.RUNPOD_POLL_TIMEOUT_SEC
    while time.monotonic() < deadline:
        time.sleep(config.RUNPOD_POLL_INTERVAL_SEC)

        st = runpod_request("GET", f"status/{job_id}")
        status = (st.get("status") or "").upper()

        if status in ("COMPLETED", "SUCCESS"):
            if st.get("output") is None: continue

            out = normalize_runpod_output(st["output"])
            if err := out.get("error"):
                raise RuntimeError(str(err))
            
            mesh = out.get("mesh")
            if not mesh:
                raise RuntimeError("RunPod output missing 'mesh' key")
            
            return str(mesh), job_id

        if status in ("FAILED", "ERROR", "CANCELLED", "TIMED_OUT"):
            raise RuntimeError(
                f"RunPod job {status}: {st.get('error') or st.get('output') or st}"
            )

    raise TimeoutError(
        f"RunPod job {job_id} did not finish within {config.RUNPOD_POLL_TIMEOUT_SEC}s"
    )
