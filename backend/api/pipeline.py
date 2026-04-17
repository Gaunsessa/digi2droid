import base64
import logging

from typing import Any

import config
import integrations
from util import download_image, image_url_from_result

log = logging.getLogger(__name__)


def run(camera_name: str) -> dict[str, Any]:
    refined = integrations.refine_search_query(camera_name)
    raw_results = integrations.google_images_light(refined)

    meta: list[dict[str, Any]] = []
    for item in raw_results[: config.TOP_N]:
        u = image_url_from_result(item)
        if not u: continue
        
        meta.append(
            {
                "url": u,
                "title": item.get("title"),
                "source": item.get("source"),
            }
        )

    if not meta:
        raise RuntimeError("No image results from SerpAPI for this query")

    downloaded: list[tuple[bytes, str]] = []
    for item in meta:
        url = item["url"]
        
        try:
            data, mime = download_image(url)
            downloaded.append((data, mime))
        except Exception:
            log.warning("Failed to download %s", url, exc_info=True)

    if not downloaded:
        raise RuntimeError("Could not download any candidate images")

    idx = integrations.pick_best_image_index(camera_name, refined, downloaded)
    idx = max(0, min(idx, len(downloaded) - 1))
    chosen_bytes, _mime = downloaded[idx]

    image_b64 = base64.b64encode(chosen_bytes).decode("ascii")
    mesh, _ = integrations.wait_for_mesh(image_b64, face_count=config.FACE_COUNT)

    return {
        "mesh": mesh,
        "refined_search_query": refined,
        "selected_index": idx,
        "candidates": meta,
    }
