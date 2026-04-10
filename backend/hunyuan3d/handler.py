import base64
import gzip
import json
import os
from pathlib import Path

import torch
import runpod

from PIL import Image
from trimesh import Trimesh
from io import BytesIO

from hy3dgen.rembg import BackgroundRemover
from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline
from hy3dgen.shapegen.postprocessors import FaceReducer

MAX_RESULT_JSON_BYTES = int(os.environ.get("MAX_RESULT_JSON_BYTES", str(20 * 1024 * 1024)))

MODEL_DIR = Path(os.environ["MODEL_DIR"])
MODEL_ID = f"{MODEL_DIR.parent.name}/{MODEL_DIR.name}"
DIT_SUBFOLDER = "hunyuan3d-dit-v2-mini-turbo"

os.environ["HY3DGEN_MODELS"] = str(MODEL_DIR.parent.parent)
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"


def load_model():
    if not MODEL_DIR.is_dir():
        raise RuntimeError(f"Model not found at {MODEL_DIR}")

    print(f"Loading model from {MODEL_DIR}")

    pipeline = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(
        MODEL_ID,
        subfolder=DIT_SUBFOLDER,
        use_safetensors=False,
        device="cuda",
    )
    pipeline.enable_flashvdm(topk_mode="merge")

    print("Model loaded successfully")

    return pipeline


def decode_image(image_base64):
    image = Image.open(BytesIO(base64.b64decode(image_base64))).convert("RGBA")

    if image.mode == "RGB":
        image = BackgroundRemover()(image)
    
    return image


def encode_mesh(mesh):
    glb_bytes = mesh.export(file_type="glb")
    if not isinstance(glb_bytes, bytes):
        raise RuntimeError(f"expected GLB bytes from export, got {type(glb_bytes)}")

    payload = base64.b64encode(gzip.compress(glb_bytes, compresslevel=9)).decode("ascii")
    return payload


def handle_job(job, pipeline):
    job_input = job.get("input", {}) or {}
    image_base64 = job_input.get("image", None)
    face_count = job_input.get("face_count", 40000)

    if not image_base64:
        return {"error": "No image provided"}

    mesh: Trimesh = pipeline(
        image=decode_image(image_base64),
        num_inference_steps=5,
        octree_resolution=380,
        num_chunks=20000,
        generator=torch.manual_seed(12345),
        output_type="trimesh",
    )[0]

    mesh = FaceReducer()(mesh, max_facenum=face_count)

    result = {
        "status": "success",
        "mesh": encode_mesh(mesh),
    }

    if len(json.dumps(result)) > MAX_RESULT_JSON_BYTES:
        return {"error": "Mesh exceeds output size limit"}

    return result


if __name__ == "__main__":
    pipeline = load_model()

    runpod.serverless.start({"handler": lambda x: handle_job(x, pipeline)})
