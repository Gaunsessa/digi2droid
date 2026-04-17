# Camera name → 3D mesh API

Async job pipeline: refine search query (OpenRouter) → SerpAPI Google Images Light → pick best image (OpenRouter vision) → RunPod Hunyuan3D worker → gzip+base64 GLB in the job result.

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENROUTER_API_KEY` | yes | [OpenRouter](https://openrouter.ai/) API key |
| `OPENROUTER_MODEL` | yes | Model slug, e.g. `google/gemini-2.5-flash-preview-05-20` (must support vision for image picking) |
| `OPENROUTER_BASE_URL` | no | Default `https://openrouter.ai/api/v1` |
| `SERPAPI_API_KEY` | yes | SerpAPI key |
| `RUNPOD_API_KEY` | yes | RunPod API key |
| `RUNPOD_ENDPOINT_ID` | yes | Serverless endpoint ID for the Hunyuan3D worker |
| `MAX_TOP_N` | no | Default `12`; capped at `20` |
| `MAX_IMAGE_BYTES` | no | Max bytes per downloaded image (default 10 MiB) |
| `RUNPOD_POLL_INTERVAL_SEC` | no | Default `2` |
| `RUNPOD_POLL_TIMEOUT_SEC` | no | Default `900` |
| `JOB_TTL_SEC` | no | In-memory job retention (default 24h) |
| `PORT` | no | Default `5000` |

## HTTP API

### `POST /v1/jobs`

Request JSON:

```json
{
  "camera_name": "Canon EOS 5D Mark IV",
}
```

**202 Accepted** response:

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status_url": "https://your-host/v1/jobs/550e8400-e29b-41d4-a716-446655440000"
}
```

### `GET /v1/jobs/{job_id}`

While running:

```json
{
  "job_id": "…",
  "status": "queued|running"
}
```

On success:

```json
{
  "job_id": "…",
  "status": "completed",
  "result": {
    "mesh": "<gzip-compressed GLB as base64 string>",
    "refined_search_query": "…",
    "selected_index": 3,
    "candidates": [{ "url": "…", "title": "…", "source": "…" }],
  }
}
```

On failure:

```json
{
  "job_id": "…",
  "status": "failed",
  "error": "Human-readable reason"
}
```

The `mesh` field matches the RunPod worker output in [../hunyuan3d/handler.py](../hunyuan3d/handler.py).
