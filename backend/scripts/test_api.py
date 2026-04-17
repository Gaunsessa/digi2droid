"""Black-box test: POST a camera name, poll the job, save the returned mesh as STL.

Usage:
    python test_api.py "Canon EOS 5D Mark IV"
    python test_api.py "Nikon Z6" --host http://localhost:1273 --out mesh.stl

Requires: httpx, trimesh
"""

from __future__ import annotations

import argparse
import base64
import gzip
import io
import sys
import time

import httpx
import trimesh


def glb_to_stl(glb_bytes: bytes, out_path: str) -> None:
    loaded = trimesh.load(io.BytesIO(glb_bytes), file_type="glb")

    if isinstance(loaded, trimesh.Scene):
        geoms = list(loaded.geometry.values())
        if not geoms:
            raise RuntimeError("GLB contains no geometry")
        mesh = trimesh.util.concatenate(geoms)
    else:
        mesh = loaded

    mesh.export(out_path, file_type="stl")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("camera_name")
    p.add_argument("--host", default="http://localhost:1273")
    p.add_argument("--out", default="mesh.stl")
    p.add_argument("--poll-interval", type=float, default=2.0)
    p.add_argument("--timeout", type=float, default=900.0)
    args = p.parse_args()

    with httpx.Client(base_url=args.host, timeout=30.0) as client:
        r = client.post("/v1/jobs", json={"camera_name": args.camera_name})
        r.raise_for_status()
        job_id = r.json()["job_id"]
        print(f"submitted job {job_id}")

        deadline = time.monotonic() + args.timeout
        while time.monotonic() < deadline:
            r = client.get(f"/v1/jobs/{job_id}")
            r.raise_for_status()
            body = r.json()
            status = body["status"]
            print(f"  status={status}")

            if status == "completed":
                glb = gzip.decompress(base64.b64decode(body["result"]["mesh"]))
                glb_to_stl(glb, args.out)
                print(f"wrote {args.out}")
                return 0

            if status == "failed":
                print(f"job failed: {body.get('error')}", file=sys.stderr)
                return 1

            time.sleep(args.poll_interval)

        print(f"timed out after {args.timeout}s", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
