import base64
import gzip
import json
import os
from io import BytesIO

import runpod
import torch
from PIL import Image
from trimesh import Trimesh

from hy3dgen.rembg import BackgroundRemover
from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline

MODEL_ID = os.environ.get("MODEL_NAME", "tencent/Hunyuan3D-2mini")
HF_CACHE_ROOT = "/runpod-volume/huggingface-cache/hub"

os.environ.setdefault("HUGGINGFACE_HUB_CACHE", HF_CACHE_ROOT)
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

_MAX_RESULT_JSON_BYTES = int(os.environ.get("MAX_RESULT_JSON_BYTES", str(20 * 1024 * 1024)))


def resolve_snapshot_path(model_id: str) -> str:
    if "/" not in model_id:
        raise ValueError(f"model_id '{model_id}' must be in 'org/name' format")

    org, name = model_id.split("/", 1)
    model_root = os.path.join(HF_CACHE_ROOT, f"models--{org}--{name}")
    refs_main = os.path.join(model_root, "refs", "main")
    snapshots_dir = os.path.join(model_root, "snapshots")

    print(f"[ModelStore] MODEL_ID: {model_id}")
    print(f"[ModelStore] Model root: {model_root}")

    if os.path.isfile(refs_main):
        with open(refs_main, "r") as f:
            snapshot_hash = f.read().strip()
        candidate = os.path.join(snapshots_dir, snapshot_hash)
        if os.path.isdir(candidate):
            print(f"[ModelStore] Using snapshot from refs/main: {candidate}")
            return candidate

    if os.path.isdir(snapshots_dir):
        versions = [
            d for d in os.listdir(snapshots_dir)
            if os.path.isdir(os.path.join(snapshots_dir, d))
        ]
        if versions:
            versions.sort()
            chosen = os.path.join(snapshots_dir, versions[0])
            print(f"[ModelStore] Using first available snapshot: {chosen}")
            return chosen

    raise RuntimeError(f"Cached model not found: {model_id}")


LOCAL_MODEL_PATH = resolve_snapshot_path(MODEL_ID)
print(f"[ModelStore] Resolved local model path: {LOCAL_MODEL_PATH}")

os.environ["HY3DGEN_MODELS"] = LOCAL_MODEL_PATH

device = "cuda"
pipeline = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(
    "",
    subfolder="hunyuan3d-dit-v2-mini-turbo",
    use_safetensors=False,
    device=device,
)
pipeline.kwargs['from_pretrained_kwargs']['model_path'] = MODEL_ID
pipeline.enable_flashvdm(topk_mode="merge")

print("[ModelStore] Model loaded from local snapshot")


def handler(job):
    job_input = job.get("input", {}) or {}
    image_base64 = job_input.get("image", None)

    if not image_base64:
        return {"error": "No image provided"}

    image = Image.open(BytesIO(base64.b64decode(image_base64))).convert("RGBA")
    if image.mode == "RGB":
        rembg = BackgroundRemover()
        image = rembg(image)

    mesh: Trimesh = pipeline(
        image=image,
        num_inference_steps=5,
        octree_resolution=380,
        num_chunks=20000,
        generator=torch.manual_seed(12345),
        output_type="trimesh",
    )[0]

    glb_bytes = mesh.export(file_type="glb")
    if not isinstance(glb_bytes, bytes):
        raise RuntimeError(f"expected GLB bytes from export, got {type(glb_bytes)}")

    payload = base64.b64encode(gzip.compress(glb_bytes, compresslevel=9)).decode("ascii")
    result = {
        "status": "success",
        "mesh_glb_encoding": "gzip_base64",
        "mesh_glb_base64": payload,
    }

    if len(json.dumps(result)) > _MAX_RESULT_JSON_BYTES:
        return {
            "error": (
                "Mesh exceeds inline output size after gzip; "
                "reduce octree_resolution / num_chunks or use object storage."
            ),
        }

    return result


runpod.serverless.start({"handler": handler})
